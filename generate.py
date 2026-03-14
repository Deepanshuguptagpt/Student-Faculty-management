import os

def generate_tree(start_path, prefix=""):
    items = sorted(os.listdir(start_path))
    pointers = ["├── "] * (len(items) - 1) + ["└── "]

    for pointer, item in zip(pointers, items):
        path = os.path.join(start_path, item)
        print(prefix + pointer + item)

        if os.path.isdir(path):
            extension = "│   " if pointer == "├── " else "    "
            generate_tree(path, prefix + extension)


if __name__ == "__main__":
    root_directory = r"C:\Users\gupta\Student Faculty management"   # change this to your project path if needed
    print(root_directory)
    generate_tree(root_directory)