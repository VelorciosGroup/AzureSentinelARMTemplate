import gui
import generate

def main(playbooks, dependsOn):
    generate.generate_master(playbooks, dependsOn)


if __name__ == "__main__":
    gui.rendergui()