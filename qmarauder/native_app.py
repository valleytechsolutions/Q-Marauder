"""GTK/WebKit desktop shell for the complete local Q-Marauder interface."""
from pathlib import Path
from urllib.parse import urlsplit
import uuid


def same_origin(candidate, home):
    try:
        value, base = urlsplit(candidate), urlsplit(home)
        return (value.scheme == base.scheme == 'http' and value.hostname == base.hostname == '127.0.0.1'
                and value.port == base.port and value.username is None and value.password is None)
    except (TypeError, ValueError): return False


def bindings():
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk, WebKit2
    return Gtk, WebKit2


def available():
    try: bindings(); return True
    except (ImportError, ValueError): return False


def launch(home, data_dir):
    Gtk, WebKit2 = bindings()
    initialized = Gtk.init_check(None)
    if not (initialized[0] if isinstance(initialized, tuple) else initialized):
        raise RuntimeError('The native app needs an accessible Debian desktop session.')
    window = Gtk.Window(title='Q-Marauder Lab')
    window.set_default_size(1100, 760)
    window.set_wmclass('q-marauder', 'Q-Marauder Lab')
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    bar = Gtk.HeaderBar(title='Q-Marauder Lab', subtitle='UNO Q · Wi-Fi & Bluetooth')
    bar.set_show_close_button(True)
    window.set_titlebar(bar)
    context = WebKit2.WebContext.new_ephemeral()
    web = WebKit2.WebView.new_with_context(context)
    settings = web.get_settings()
    settings.set_enable_developer_extras(False)
    settings.set_javascript_can_open_windows_automatically(False)
    status = Gtk.Label(label='Local toolkit · shared with the portrait touchscreen')
    status.set_xalign(0)
    status.set_margin_start(12); status.set_margin_end(12)
    status.set_margin_top(6); status.set_margin_bottom(6)
    home_button = Gtk.Button(label='Lab')
    home_button.connect('clicked', lambda *_: web.load_uri(home))
    reload_button = Gtk.Button(label='Reload')
    reload_button.connect('clicked', lambda *_: web.reload())
    bar.pack_start(home_button); bar.pack_end(reload_button)

    def policy(_view, decision, kind):
        if kind in (WebKit2.PolicyDecisionType.NAVIGATION_ACTION, WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION):
            uri = decision.get_navigation_action().get_request().get_uri()
            if kind == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION or not same_origin(uri, home):
                decision.ignore()
                status.set_text('External navigation is blocked in this local app window.')
                return True
        return False

    def download_started(_context, download):
        if not same_origin(download.get_request().get_uri(), home):
            download.cancel(); return
        outcome = {'failed': False}
        def failed(_job, error):
            outcome['failed'] = True
            status.set_text('Export failed: '+str(error))
        def destination(job, suggested):
            suffix = Path(suggested).suffix.lower()
            if suffix not in ('.csv', '.json', '.pcap'):
                status.set_text('Unsupported export type.'); job.cancel(); return True
            exports = Path(data_dir)/'exports'
            exports.mkdir(parents=True, exist_ok=True, mode=0o700)
            target = exports/('q-marauder-'+uuid.uuid4().hex+suffix)
            job.set_destination(target.resolve().as_uri())
            def finished(*_):
                if not outcome['failed']:
                    if target.is_file():
                        target.chmod(0o600)
                        status.set_text('Export saved: '+str(target))
                    else: status.set_text('Export did not create a file.')
            job.connect('finished', finished)
            return True
        download.connect('decide-destination', destination)
        download.connect('failed', failed)

    context.connect('download-started', download_started)
    web.connect('decide-policy', policy)
    web.connect('permission-request', lambda _web, request: (request.deny(), True)[1])
    web.connect('load-failed', lambda _web, _event, _uri, error: (status.set_text('Local service unavailable: '+str(error)), False)[1])
    box.pack_start(web, True, True, 0); box.pack_end(status, False, False, 0)
    window.add(box)
    window.connect('destroy', Gtk.main_quit)
    web.load_uri(home)
    window.show_all()
    Gtk.main()
