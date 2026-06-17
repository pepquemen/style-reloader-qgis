def classFactory(iface):
    from .style_reloader import StyleReloader
    return StyleReloader(iface)