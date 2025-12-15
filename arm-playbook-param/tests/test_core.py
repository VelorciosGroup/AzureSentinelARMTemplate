import copy
from arm_param_app.core import replace_literals, add_parameter_definitions


def test_replace_literals_basic():
    template = {
        "parameters": {},
        "name": "MY_PLAYBOOK",
        "props": {
            "value": "MY_PLAYBOOK"
        }
    }
    lit_to_param = {"MY_PLAYBOOK": "playbookName"}
    new_tpl = replace_literals(copy.deepcopy(template), lit_to_param)
    assert new_tpl["name"] == "[parameters('playbookName')]"
    assert new_tpl["props"]["value"] == "[parameters('playbookName')]"


def test_add_parameter_definitions():
    template = {"parameters": {}}
    lit_to_param = {"MY_PLAYBOOK": "playbookName"}
    add_parameter_definitions(template, lit_to_param)
    assert "playbookName" in template["parameters"]
    assert template["parameters"]["playbookName"]["defaultValue"] == "MY_PLAYBOOK"
