import socket # we can create a socket that can send and receive data from other computers
import ssl # provides a way to secure our connection using secure sockets layer (SSL) and transport layer security (TLS) protocols
import tkinter # library is used for making GUIs
import tkinter.font

WIDTH, HEIGHT = 800, 800 # global constants
HSTEP, VSTEP = 13, 18 # seperation of characters in x and y direction
SCROLL_STEP = 100 # scrolling sensitivity
FONTS = {} # cache fonts for performance
BLOCK_ELEMENTS = [
        "html", "body", "article", "section", "nav", "aside",
        "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
        "footer", "address", "p", "hr", "pre", "blockquote",
        "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
        "figcaption", "main", "div", "table", "form", "fieldset",
        "legend", "details", "summary"
    ]


def get_font(size, weight, style): # helper function to cache fonts
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font) # label helps speed up font metrics
        FONTS[key] = (font, label)
    return FONTS[key][0]

class URL: # we need to extract the host name and path from URL, creat a socket, send a request. and receive a response
    def __init__(self, url): # class constructor (self parameter is always the first of any method)
        self.scheme, url = url.split("://", 1) # splits between :// with a maxsplit of 1 because there should only be 1 ://
        assert self.scheme in ["http", "https"] # assert evaluates a given condition (if true is keeps going if not it gives AssertionError)
        if self.scheme == "http":
            self.port = 80 # encrypted HTTP connections usualyl use port 443 not 80
        elif self.scheme == "https":
            self.port = 443
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1) # tuple unpacking, 2 values returned by the split (1st one to self.host and 2nd to url)
        self.path = "/" + url
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port) # convert the string from the URL to an integer so we can use it in the socket

    def request(self): # download the web page at the URL
        s = socket.socket( # creates a socket object named s
            family=socket.AF_INET, # addres family which is how we gonna find the other computers
            type=socket.SOCK_STREAM, # which conversion is gonna happen (so we can send arbitrary amounts of data)
            proto=socket.IPPROTO_TCP, # the type of protocol I am gonna use (how the computers establish a connection)
        )
        s.connect((self.host, self.port)) # need to tell socket to connect using a host and a port (port depends on protocol but for now I will use 80)
        if self.scheme == "https":
            ctx = ssl.create_default_context() # sets up default secure settings
            s = ctx.wrap_socket(s, server_hostname=self.host) # takes normal socket and wraps it with encryption, second part is for server name identification so that servers with multiple domains on one ip work

        request = "GET {} HTTP/1.0\r\n".format(self.path) # \r\n together start a new line
        request += "Host: {}\r\n".format(self.host)
        request += "\r\n" # need this to that we have an extra blank line at the end of the request or else the other computer will keep waiting
        s.send(request.encode("utf8")) # send method sends request to the server

        response = s.makefile("r", encoding="utf8", newline="\r\n") # makefile returns file-like object that has every byte we receive from the server (utf8 turns bytes into string or to letters)
        statusline = response.readline() # reads the status line (ex. HTTP/1.0 200 OK)
        version, status, explanation = statusline.split(" ", 2) # splits status line into 3 parts (HTTP/1.0, 200, OK)

        response_headers = {} # empty dictionary
        while True: # keeps reading lines until it reaches blank line
            line = response.readline() # reads one line at a time from response
            if line == "\r\n": break # how it ends
            header, value = line.split(":", 1) # splits into the header name and header value between :
            response_headers[header.casefold()] = value.strip() # casefold makes header name lowercase and uniform and value.strip removes any spaces or newline characters around header value
            '''
                'content-type': 'text/html',
                'content-length': '1234',
            '''
        assert "transfer-encoding" not in response_headers # does not include transfer-encoding header
        assert "content-encoding" not in response_headers # does not include content-encoding header

        content = response.read() # this is how to get the sent data after all those headers (usually the html we want)
        s.close() # closses the socket connection to the server
        return content # response we need

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def paint(self):
        return [] # nothing to paint
    

    def layout(self):
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        
        # Create the first child layout with this DocumentLayout as its parent
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
        self.height = child.height

class BlockLayout: # handles the layout logic
    
    def paint(self):
        cmds = []
        if isinstance(self.node, Element) and self.node.tag == "pre": # background has to be drawn below the text
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))
        return cmds
    
    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous: # y is a little different, starts at top edge origonally but if there is a previous sibling it starts right after it
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        mode = self.layout_mode() # calls this to decide if its block or inline
        if mode == "block":
            previous = None # keeps track of previous sibling element
            for child in self.node.children:
                next = BlockLayout(child, self, previous) # creates a BlockLayout object for that child
                self.children.append(next) # add this new layout object "next" to self.children 
                previous = next # updates previous to be this new child (for the next iteration)
        else: # if its an inline layout
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12

            self.line = []
            self.recurse(self.node) # walks through the nodes text and children, adding words for drawing
            self.flush() # draws the line, moves to next line
        for child in self.children:
            child.layout() # layout method needs to recursivley call layout to the children can construct their children and so on
        if mode == "block":
            self.height = sum([
                child.height for child in self.children]) # height should be the sum of its children's heights
        else:
            self.height = self.cursor_y
    

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline" # if the node is a piece of text it should be inline
        elif any([isinstance(child, Element) and \
                  child.tag in BLOCK_ELEMENTS          # inbetween [ ] is a list of comprehension. checks if the child is an HTML element and if the element is a block element (hence return block)
                  for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"

    def layout_intermediate(self): 
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
    
    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
    
    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.line = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

        # this is how layout is usually triggered manually later
        # self.layout()

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP

    def word(self, word):
        font = get_font(self.size, self.weight, self.style) # get cached font
        w = font.measure(word) # measure word width
        if self.cursor_x + w > self.width: # check if word fits on line
            self.flush() # start new line
        self.line.append((self.cursor_x, word, font)) # store word and position
        self.cursor_x += w + font.measure(" ") # move x cursor

    def flush(self): # loops through the list and draws each character with its respective x and y position
        if not self.line: return # skip if line is empty
        metrics = [font.metrics() for x, word, font in self.line] # get font metrics
        max_ascent = max([m["ascent"] for m in metrics]) # find tallest ascent
        max_descent = max([m["descent"] for m in metrics]) # find deepest descent
        baseline = self.cursor_y + 1.25 * max_ascent # calculate baseline with leading
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent") # align to baseline
            self.display_list.append((x, y, word, font)) # add to display list
        self.cursor_y = baseline + 1.25 * max_descent # move y cursor
        self.cursor_x = 0 # reset x cursor
        self.line = [] # clear current line

class HTMLParser:
    SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
    ]
    HEAD_TAGS = [ # tags that go in the <head> element
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                attributes[key.casefold()] = value
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self. add_tag("html")
            elif open_tags == ["html"] \
                and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and \
                tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break
    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1: # turns the incomplete tree to a complete one by finishing any unfinished nodes
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    
    def parse(self):
        text = "" # gets characters between the tags
        in_tag = False # am I inside an HTML tag?
        for c in self.body: # loops over every character in the HTML string
            if c == "<":
                in_tag = True
                if text: self.add_text(text) # empty string is considered false, non-empty is considered true
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text: # if leftover text at the end, add it
            self.add_text(text)
        return self.finish() # returns the final parsed structure
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1] # sets the last element to the parent
        node = Text(text, parent) 
        parent.children.append(node)


    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return # ignores tags that start with ! which throws out doctype declarations and comments 
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
    
    def __init__(self, body): # body is a string of HTML
        self.body = body
        self.unfinished = [Element("html", {}, None)]  # add a fake root node to start, starts empty but as parser reads tokens the list fills up (list that tracks HTML tags), STACK type of list

class Browser:
    def __init__(self): # constructor method
        self.scroll = 0 # how far you've scrolled
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, 
            width=WIDTH,        # creates a canvas widget where we can draw graphics
            height=HEIGHT
        )
        self.canvas.pack()
        self.window.bind("<Down>", self.scrolldown) # event handler

    def scrolldown(self, e):
        max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0) # keeps it from scrolling past the bottom
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()

    def load(self, url):
        body = url.request() # download the web page at the URL
        self.nodes = HTMLParser(body).parse() # an HTML stripper, body is a string of HTML content
        self.document = DocumentLayout(self.nodes)
        self.document.layout()    # beginning of our layout tree
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.display_list = []
        paint_tree(self.document, self.display_list)
        for cmd in self.display_list: # loops through the list and draws each character with its respective x and y position
            if cmd.top > self.scroll + HEIGHT: continue # skips characters below the viewing window
            if cmd.bottom < self.scroll: continue # skips characters above the viewing window
            cmd.execute(self.scroll, self.canvas) # when the self.scroll is changed the page will scroll up and down accordingly

class Text: # need tokens to evolve into nodes, so gotta add a list of children and a parent pointer to each one
    def __repr__(self):
        return repr(self.text)
    
    def __init__(self, text, parent): # this class will represent the text at the leaf of each tree
        self.text = text
        self.children = []
        self.parent = parent

class Element: 
    def __repr__(self):
        return "<" + self.tag + ">"
    
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = [] # text nodes don't have children but its here for consistency
        self.parent = parent

class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace") # want to skip offscreen graphics commands
    
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw')
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
    
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color)
def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


if __name__ == "__main__": # main function (only run code inside this block if the file is being run directly)
    import sys
    browser = Browser()
    browser.load(URL(sys.argv[1]))
    browser.window.mainloop()
