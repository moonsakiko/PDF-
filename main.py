import flet as ft

def main(page: ft.Page):
    page.add(ft.Text("能看到我吗？如果看到我，说明环境是好的！"))

ft.app(target=main)
