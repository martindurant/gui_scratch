#! /usr/bin/env python

import panel as pn
from panel import widgets, pane, layout
pn.extension()
space = '\u2003'
detail = """container: dataframe
driver: csv
args:
  urlpath: http://github.com//blah
metadata:
  plots:
    basic:
      kind: line"""
d = """dtype:
  name: str
shape: (100, 3)
"""
kw = dict(width_policy='max', sizing_mode='stretch_width')


class GUI:
    def __init__(self):
        cats = widgets.MultiSelect(
            name="Data",
            value=[],
            options=[
                "▼ builtin",
                "  ▶ seas".replace(" ", space),
                "▼ nucleus",
                "  ▼ Albert's".replace(" ", space),
                "    ⌗ example".replace(" ", space),
                "▼ session",
                "  ▶ mycat".replace(" ", space),
                "  𝛴 other".replace(" ", space)
            ],
            size=12,
            scroll=True
        )
        up = widgets.Button(name="Upload", disabled=True)
        refr = widgets.Button(name="Refresh", disabled=True)
        share = widgets.Button(name="Sharing", disabled=True)
        sear = widgets.Button(name="Search", disabled=True)
        left_buttons = layout.Row(
            up, refr, share, sear, **kw
        )
        left = pn.Column(
            cats, left_buttons, **kw
        )

        details = pane.Markdown(
            f"""```yaml\n{detail}\n```""",
            scroll=True
        )

        copy = widgets.Button(name="Copy code")
        plot = widgets.Button(name="Plot...")
        disc = widgets.Button(name="Discover")
        right_buttons = layout.Row(
            copy, plot, disc, **kw
        )

        wbox = layout.WidgetBox(
            pn.widgets.TextInput(name="textp", placeholder="text thing"),
            pn.widgets.FloatInput(name="floatp"), scroll=True,
            **kw
        )

        discovered = pn.pane.Markdown(
            f"""```yaml\n{d}\n```""",
            scroll=True
        )

        right = pn.Column(
            details, wbox, right_buttons, discovered, **kw
        )

        self.main = pn.Row(
            left, right, **kw
        )

    def show(self):
        self.main.show()


if __name__ == "__main__":
    g = GUI()
    g.show()
