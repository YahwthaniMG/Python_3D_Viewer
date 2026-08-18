import argparse
import sys

from . import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualizador 3D de modelos OBJ")
    parser.add_argument(
        "obj_file_path", nargs="?", default="OBJs/cup.obj",
        help="Ruta al archivo .obj a visualizar (default: OBJs/cup.obj)",
    )
    args = parser.parse_args()

    try:
        app.run(args.obj_file_path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
