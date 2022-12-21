from html.parser import HTMLParser


class HtmlPrinter(HTMLParser):
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_str = " ".join(k if v is None else f"{k}={v}" for k, v in attrs)
        print(f"Started making element: <{tag}{f' {attr_str} ' if attr_str else ''}>")

    def handle_data(self, data: str) -> None:
        print(f"Adding element body text: {data!r}")

    def handle_endtag(self, tag: str) -> None:
        print(f"Finished creating element: </{tag}>")


html_printer = HtmlPrinter()
html_printer.feed('<h1 color="blue">Hello, <b>world</b>!</h1>')
