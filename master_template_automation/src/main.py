import gui
import generate


def main(playbooks, master_template_name):
    generate.generate_master(playbooks, master_template_name)


if __name__ == "__main__":
    playbooks = gui.rendergui()