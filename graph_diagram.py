from agent import _compiled_graph


def main() -> None:
    graph = _compiled_graph.get_graph()
    print(graph.draw_mermaid())
    try:
        png = graph.draw_mermaid_png()
        with open("graph.png", "wb") as f:
            f.write(png)
        print("\nSaved graph.png")
    except Exception as e:
        print(f"\nPNG render skipped: {e}")


if __name__ == "__main__":
    main()
