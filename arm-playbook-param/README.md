Para ejecutar:

PYTHONPATH=src python3 -m arm_param_app.cli   -f examples/enrich_raw.json   -o examples/wompt.json   --name Enrich_Playbook_Name  --externalid Enrich_Playbook_ExternalID

Otro ejemplo 

 PYTHONPATH=src python3 -m arm_param_app.cli \
  -f examples/auth_raw.json \
  -o examples/wompt.json \
  --name WOTOTOTOT \
  --externalid BBBBBBBBBBBBB \
  --keyvault keyvault_name keyvault_ClientID keyvault_Secret keyvault_BaseUrl
usage: cli.py [-h] -f INPUT -o OUTPUT [--name PLAYBOOK_NAME_PARAM] [--externalid EXTERNALID_NAMES] [--keyvault KEYVAULT_NAMES]
cli.py: error: unrecognized arguments: keyvault_ClientID keyvault_Secret keyvault_BaseUrl
