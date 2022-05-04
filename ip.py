import fsspec.utils
import ipywidgets as ip
from IPython.display import Code, display
from ipytree import Tree, Node as IPyNode
import intake
from traitlets import Unicode
import panel as pn
import sys
import yaml.representer
import logging
import yaml
logger = logging.Logger("intake_ipyw")
fsspec.utils.setup_logging(logger)

try:
    import intake_nucleus
    from intake_nucleus.nucleus.api import NucleusAPI
    api = NucleusAPI()
except ImportError:
    intake_nucleus = False
main = sys.modules["__main__"]


class MYRep(yaml.representer.Representer):
    def represent_undefined(self, data):
        return self.represent_str("{...}")


yaml.representer.Representer.add_multi_representer(
    object, MYRep.represent_undefined)


bstyle = dict(
    style = {'width': 'initial'},
    layout = ip.Layout(width='100px'),
)
icons = {
    "catalog": "folder",  # "folder by default
    "dataframe": "database",
    "array": "grid"
}
ex = [None]


def log_callback(func):
    def _(*args, **kwargs):
        logger.debug(str((func.__name__, args, kwargs)))
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.debug(str(e))
            ex[0] = e
            raise
    return _



class Node(IPyNode):
    path = Unicode()


class GUI:
    def __init__(self):
        self.session = Node("session", path="session")
        self.builtin = Node("built-in")
        self.nuc = Node("nucleus", path="nucleus")
        tt = Tree([
            self.builtin,
            self.nuc,
            self.session
        ], multiple_selection=True, layout=ip.Layout(height='100%', width="100%", overflow_y='scroll'))
        tree = ip.Box([tt],
            style = {'height': 'initial'},
            layout = ip.Layout(height='80%'),
        )

        tt.observe(self.tree_select, names='selected_nodes')
        self.upload_button = ip.Dropdown(options=["Upload_to...", "New..."], **bstyle)

        refresh = ip.Button(description="Refresh", **bstyle)
        left_buttons = ip.HBox([
            self.upload_button,
            refresh,
            ip.Button(description="Sharing", **bstyle),
            ip.Button(description="Search", **bstyle),
            ],
            layout=ip.Layout(overflow="hidden")
        )
        refresh.on_click(self.make_session)

        left = ip.VBox([tree, left_buttons], width="40%", height="80%")

        detail = ip.HTML(layout=ip.Layout(height='50%', width="100%", overflow_y="auto"),
                         style={'height': 'initial'})
        self.detail = detail

        self.pars = ip.VBox(
            [
                ip.HTML("Parameters"),
                ip.Text(value="value", description="text_thing"),
                ip.FloatText(description="number"),
                ip.DatePicker(description="datetime"),
                ip.Checkbox(value=True, description="bool")
            ],
            layout=ip.Layout(height='15%', width="100%", overflow_y='scroll', border="inset")
        )
        self.out = ip.HTML(layout=ip.Layout(height='20%', width="100%", overflow_y='auto'))

        self.plot_button = ip.Dropdown(options=["Plot..."], **bstyle)
        code_button = ip.Button(description="Code")
        discover_button = ip.Button(description="Discover")
        right_buttons = ip.HBox(
            [
                code_button,
                self.plot_button,
                discover_button
            ],
            layout=ip.Layout(overflow="hidden")
        )
        self.plot_button.observe(self.plot_clicked, "value")
        code_button.on_click(self.code_clicked)
        discover_button.on_click(self.discover_clicked)

        right = ip.VBox([detail, self.pars, right_buttons, self.out],
                        layout=ip.Layout(width="60%", height="80%"),
                        style={"height": "initial"})

        self.plot = ip.HBox([], layout=ip.Layout(display="none", width="100%", height="80%"))
        self.main = ip.HBox([left, right])

        self.outer = ip.VBox([self.main, self.plot], width="100%")
        self.selected = []

        # make tree
        self.make_builtin()

    def make_builtin(self):
        import intake
        nodes = []
        for k, v in intake.cat._entries.items():
            if k == 'anaconda_catalogs':
                # already handles separately
                continue
            nodes.append(Node(path=f"intake.cat.{k}", name=k, icon=icons[v.container]))
        self.builtin.nodes = tuple(nodes)

    def make_nuc(self):
        if intake_nucleus and api.logged_in:
            try:
                nodes = []
                for k, v in intake.cat.anaconda_catalogs._entries.items():
                    nodes.append(Node(path=f"intake.cat.anaconda_catalogs.{k}",
                                      name=k, icon=icons[v.container]))
                self.nuc.nodes = tuple(nodes)
                self.was_logged_in = True
                self.upload_button.options = [
                     "Upload to..."
                ] + list(intake.cat.anaconda_catalogs._entries) + ["New..."]
            except Exception as e:
                self.error = str(e)
        else:
            self.nuc.disabled = True
            self.nuc.opened = False
            self.was_logged_in = False

    def make_session(self, _=None):
        nodes = []
        for k, v in main.__dict__.items():
            if k.startswith("_"):
                continue
            if isinstance(v, intake.source.base.DataSourceBase):
                nodes.append(Node(k, path=f"session.{k}", icon=icons[v.container]))
        self.session.nodes = tuple(nodes)

    @property
    def selected_data(self):
        roots = {
            "intake": intake,
            "session": main
        }
        parts = self.selected.path.split(".")
        here = roots[parts[0]]
        for part in parts[1:]:
            here = getattr(here, part)
        return here

    @log_callback
    def tree_select(self, change):
        selected = change["new"]
        if isinstance(selected, tuple):
            selected = selected[0]
        self.selected = selected
        if selected.path == "nucleus":
            return self.make_nuc()
        if selected.path == "session":
            return self.make_session()
        here = self.selected_data
        if here.container == "catalog":
            nodes = []
            for k, v in here._entries.items():
                # TODO: some cats are huge, only expand on demand or only allow search
                nodes.append(Node(path=f"{selected.path}.{k}",
                                  name=k, icon=icons[v.container]))
            selected.nodes = tuple(nodes)
        else:
            self.out.value = ""
            detail = here._yaml()["sources"]
            yam = yaml.dump(detail, default_flow_style=False)
            self.detail.value = Code(data=yam, language="yaml"
                                     )._repr_html_().replace('class="nt"', 'style="color:MediumSeaGreen;"')
            self.plot.layout.display = "none"
            if here.plots:
                self.plot_button.options = ["Plot..."] + here.plots
                self.plot_button.disabled = False
            else:
                self.plot_button.options = ["Plot..."]
                self.plot_button.disabled = True
        nodes = []
        for up_dict in here.describe()["user_parameters"]:
            # generate parameter-specific widgets
            pass


    @log_callback
    def plot_clicked(self, ev):
        if ev["new"] == "Plot...":
            self.plot.layout.display = "none"
        else:
            panel = getattr(self.selected_data.plot, ev["new"])()
            panel_plot = pn.ipywidget(panel)
            self.plot.children = [panel_plot]
            self.plot.layout.display = "block"

    @log_callback
    def code_clicked(self, _):
        path = self.selected.path
        if path.startswith("session."):
            path = path[len("session."):]
        if path not in ["", "nucleus", "built-in", "session"]:
            self.out.value = Code(f"import intake\n{path}")._repr_html_().replace('class="kn"',
                                                                                  'style="color:MediumSeaGreen;"')
        else:
            self.out.value = ""

    @log_callback
    def discover_clicked(self, _):
        disc = self.selected_data.discover()
        disc.pop("metadata")
        self.out.value = Code(
            yaml.dump(disc, default_flow_style=False), language="yaml")._repr_html_().replace('class="nt"',
                                                                                              'style="color:MediumSeaGreen;"')

    def _ipython_display_(self, **kwargs):
            return self.outer._ipython_display_(**kwargs)

    def show(self):
        return self.outer
