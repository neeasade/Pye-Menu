from math import pi, sin, cos, atan2, sqrt
from collections import defaultdict
import cairo
import gi
gi.require_versions({'Gtk': '3.0', 'PangoCairo': '1.0'})
from gi.repository import Gtk, Gdk, Pango, PangoCairo

class FontCache(dict):
    def __missing__(self, key):
        self[key] = Pango.FontDescription.from_string(key)
        return self[key]
font_cache = FontCache()

class MenuItem:
    def __init__(self, label, action=None):
        self.label = label
        self._layout = None
        self.action = action or self.get_index

    def set_label(self, label):
        self.label = label

    def set_index(self, index):
        self.index = index

    def get_index(self):
        return self.index

    def add_centred_text(self, cairo, pango, x, y):
        # Text
        layout = Pango.Layout(pango)
        layout.set_font_description(font_cache["sans-serif 12"])
        layout.set_markup(self.label)
        w,h = layout.get_pixel_size()
        cairo.move_to(x-w/2, y-h/2)
        PangoCairo.show_layout(cairo, layout)

class PyeMenu(Gtk.Window):
    def __init__(self, *args,
                 action_handler = (lambda v: print(v) if v is not None else v),
                 width = 500, height = 500, rotate = 0,
                 radius = 200, cancel_radius = 20, accept_radius = 250,
                 alpha = "#ffffff00", fg = "#657b83", bg = "#fdf6e3",
                 border="#657b83", hi_fg = "#22aa22", hi_bg = "#cceecc",
                 cancel = "#fdf6e3", hi_cancel = "#aa2222", accept = "#eee8d5"):
        super().__init__()
        keyword_args = {k:v for k,v in locals().items() if k not in ['self', 'args']}
        self.__dict__.update(keyword_args)
        self.canonicalize_colors()

        self.connect("delete-event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)

        self.items = []
        self.selected = None
        for arg in args:
            self.add_item(arg)

        self.set_size_request(self.width, self.height)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.set_title("Pye Menu")
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_decorated(False)
        self.set_role("pye-menu")
        self.set_wmclass("pye-menu", "pye-menu")

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK)
        self.do_screen_changed(None, None)

    def add_item(self, name_or_MenuItem):
        item = name_or_MenuItem
        if not isinstance(item, MenuItem):
            item = MenuItem(item)
        item.set_index(len(self.items))
        self.items.append(item)
        self.pye_arc = 2*pi / len(self.items)
        self.pye_offset = float(self.rotate)*pi/180-self.pye_arc/2

    def canonicalize_colors(self):
        for col in "fg bg border hi_fg hi_bg cancel hi_cancel accept".split(" "):
            c = self.__dict__[col]
            if type(c) == str:
                c1 = ( (int(c[a:a+2], base=16)/255) for a in [1, 3, 5])
                self.__dict__[col] = tuple(c1)
        self.alpha = tuple( (int(self.alpha[a:a+2], base=16)/255) for a in [1, 3, 5, 7])

    def to_cartesian(self, phi, r):
        """Gives the cartesian coordinate for the passed in angular ones
        (cartesian is centered top-left, angular at the middle)
        """
        return (self.width/2 + r*cos(phi), self.height/2 + r*sin(phi))

    def to_angular(self, x, y):
        """Gives the angular coordinate (phi, r) for the passed in cartesian
        ones (cartesian is centered top-left, angular at the middle)
        """
        x, y = x-self.width/2, y-self.height/2
        return (atan2(y, x) % (2*pi),
                sqrt(x**2 + y**2))

    def do_screen_changed(self, old_screen, user_args=None):
        """This ensures we use the right 'visual' which is stuff like the
        possibility for alpha in the background.
        """
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        self.supports_alpha = screen.is_composited()
        self.set_visual(visual or screen.get_system_visual())

    def do_draw(self, context, user_args=None):
        """This draws the pie menu.
        """
        # First draw background alpha
        if self.supports_alpha:
            context.set_source_rgba(1.0, 1.0, 1.0, 0.0)
            context.set_operator(cairo.OPERATOR_SOURCE)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)
        context.paint()

        # The background circle
        context.arc(self.width/2, self.height/2,
                    self.radius, 0, 2*pi)
        context.set_source_rgb(1, 1, 1)
        context.fill()

        # The values
        sweep = 2*pi / len(self.items)
        angle = -sweep/2
        for item in self.items:
            context.save()
            self.slice_path(context, angle, sweep)
            if self.is_selected(angle, sweep):
                context.set_source_rgb(0, 1, 0)
                context.fill_preserve()
                context.set_source_rgb(0, 0, 0)
            else:
                context.set_source_rgb(0, 0, 0)
            context.clip_preserve()
            context.stroke()
            if self.is_selected(angle, sweep):
                context.set_source_rgb(1, 1, 1)
            item.add_centred_text(context, self.get_pango_context(),
                          *self.to_cartesian(angle+sweep/2, self.radius/2))
            context.restore()
            angle += sweep

        # Cancel circle
        context.new_path()
        context.arc(*self.to_cartesian(0, 0)+(self.cancel_radius, 0, 2*pi))
        if self.selected != None:
            context.set_source_rgb(1, 1, 1)
        else:
            context.set_source_rgb(1, 0, 0)
        context.fill_preserve()
        context.set_source_rgb(0, 0, 0)
        context.stroke()

        # Stop propagating the draw event
        return True

    def do_button_release_event(self, event, user_args=None):
        if self.selected != None:
            sweep = 2*pi/len(self.items)
            print(int(((self.selected+sweep/2)%(2*pi)) / sweep))
        self.hide()
        self.destroy()
        Gtk.main_quit()

        # Stop propagating the release
        return True

    def do_motion_notify_event(self, event, user_args=None):
        x, y = event.x, event.y
        phi, r = self.to_angular(x, y)
        if r > self.cancel_radius and r < self.radius:
            self.selected = phi
        else:
            self.selected = None
        self.queue_draw()

    def is_selected(self, angle, sweep):
        return self.selected != None and \
            ((self.selected-angle)%(2*pi)) <= sweep

    def slice_path(self, context, angle, sweep):
        xmid, ymid = self.to_cartesian(0, 0)
        context.move_to(xmid, ymid)
        context.line_to(*self.to_cartesian(angle, self.radius))
        context.arc(xmid, ymid, self.radius, angle, angle+sweep)

#win = PyeMenu("Foo", "Bar", "Baz", "Quux", "What duck?")
#win.show_all()
#Gtk.main()
