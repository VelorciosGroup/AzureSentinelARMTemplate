<table>
  <tr>
    <th>Integración</th>
    <th>Deploy</th>
    <th>Contenido</th>
  </tr>

  <!-- SOPHOS -->
  <tr>
    <td><b>Sophos Client Integration for Azure Sentinel</b></td>
    <td>
      <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FSophos%2FDeploy_Sophos.json">
        <img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure" width="1000px" />
      </a>
    </td>
    <td>
      <ul>
        <li>Cliente_Action_Sophos_Block_Domain_Playbook.json</li>
        <li>Cliente_Action_Sophos_Block_Hash_Playbook.json</li>
        <li>Cliente_Action_Sophos_Block_Incident_Domains_Playbook.json</li>
        <li>Cliente_Action_Sophos_Block_Incident_Hashes_Playbook.json</li>
        <li>Cliente_Action_Sophos_Block_Incident_IPs_Playbook.json</li>
        <li>Cliente_Action_Sophos_Block_IP_Playbook.json</li>
        <li>Cliente_Action_Sophos_Device_Isolation_Playbook.json</li>
        <li>Cliente_Action_Sophos_Launch_Antivirus_Playbook.json</li>
        <li>Cliente_OrchestatorPart_Sophos_Block_IOC_Playbook.json</li>
        <li>Cliente_Enrich_Sophos_Get_Device_Info_Playbook.json</li>
        <li>Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook.json</li>
        <li>Deploy_Sophos.json</li>
      </ul>
    </td>
  </tr>

  <!-- API PARSER -->
  <tr>
    <td><b>API Username Parser for Azure Sentinel</b></td>
    <td>
      <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FAPI_parser_usernames%2FDeploy_API_Parser.json">
        <img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure" width="140px" />
      </a>
    </td>
    <td>
      <ul>
        <li>Cliente_Action_API_Parser_Account_Entity_Playbook.json</li>
        <li>Cliente_Action_API_Parser_Alert_Playbook.json</li>
        <li>Cliente_Action_API_Parser_Incident_Playbook.json</li>
        <li>Cliente_OrchestatorPart_API_Parser_Playbook.json</li>
        <li>Cliente_OrchestatorPart_API_Petition.json</li>
        <li>Deploy_API_Parser.json</li>
      </ul>
    </td>
  </tr>

  <!-- CROWDSTRIKE -->
  <tr>
    <td><b>CrowdStrike Falcon Integration for Azure Sentinel</b></td>
    <td>
      <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FCrowdStrike%2FDeploy_CrowdStrike.json">
        <img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure" width="140px" />
      </a>
    </td>
    <td>
      <ul>
        <li>Cliente_Action_CrowdStrike_Block_Hash_Playbook.json</li>
        <li>Cliente_Action_CrowdStrike_Block_Incident_Hashes_Playbook.json</li>
        <li>Cliente_Action_CrowdStrike_Device_Isolation_Playbook.json</li>
        <li>Cliente_OrchestatorPart_CrowdStrike_Auth_Playbook.json</li>
        <li>Cliente_OrchestatorPart_CrowdStrike_Block_IOC_Playbook.json</li>
        <li>Cliente_Enrich_CrowdStrike_Device_Info_Playbook.json</li>
        <li>Cliente_Enrich_CrowdStrike_Recent_Alerts_Playbook.json</li>
        <li>Deploy_CrowdStrike.json</li>
      </ul>
    </td>
  </tr>

</table>




# Integraciones de Azure Sentinel

<div style="display:flex; gap:15px; flex-wrap:wrap;">

  <!-- SOPHOS -->
  <div style="border:1px solid #ccc; border-radius:10px; padding:15px; width:320px; box-shadow:2px 2px 5px rgba(0,0,0,0.1);">
    <h3>🛡️ Sophos Client Integration</h3>
    <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FSophos%2FDeploy_Sophos.json">
      <img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure" width="120px"/>
    </a>
    <ul>
      <li>📄 Cliente_Action_Sophos_Block_Domain_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Block_Hash_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Block_Incident_Domains_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Block_Incident_Hashes_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Block_Incident_IPs_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Block_IP_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Device_Isolation_Playbook.json</li>
      <li>📄 Cliente_Action_Sophos_Launch_Antivirus_Playbook.json</li>
      <li>📄 Cliente_OrchestatorPart_Sophos_Block_IOC_Playbook.json</li>
      <li>📄 Cliente_Enrich_Sophos_Get_Device_Info_Playbook.json</li>
      <li>📄 Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook.json</li>
      <li>✅ Deploy_Sophos.json</li>
    </ul>
  </div>

  <!-- API PARSER -->
  <div style="border:1px solid #ccc; border-radius:10px; padding:15px; width:320px; box-shadow:2px 2px 5px rgba(0,0,0,0.1);">
    <h3>🔍 API Username Parser</h3>
    <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FAPI_parser_usernames%2FDeploy_API_Parser.json">
      <img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure" width="120px"/>
    </a>
    <ul>
      <li>📄 Cliente_Action_API_Parser_Account_Entity_Playbook.json</li>
      <li>📄 Cliente_Action_API_Parser_Alert_Playbook.json</li>
      <li>📄 Cliente_Action_API_Parser_Incident_Playbook.json</li>
      <li>📄 Cliente_OrchestatorPart_API_Parser_Playbook.json</li>
      <li>📄 Cliente_OrchestatorPart_API_Petition.json</li>
      <li>✅ Deploy_API_Parser.json</li>
    </ul>
  </div>

  <!-- CROWDSTRIKE -->
  <div style="border:1px solid #ccc; border-radius:10px; padding:15px; width:320px; box-shadow:2px 2px 5px rgba(0,0,0,0.1);">
    <h3>🦅 CrowdStrike Falcon Integration</h3>
    <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FCrowdStrike%2FDeploy_CrowdStrike.json">
      <img src="https://aka.ms/deploytoazurebutton" alt="Deploy to Azure" width="120px"/>
    </a>
    <ul>
      <li>📄 Cliente_Action_CrowdStrike_Block_Hash_Playbook.json</li>
      <li>📄 Cliente_Action_CrowdStrike_Block_Incident_Hashes_Playbook.json</li>
      <li>📄 Cliente_Action_CrowdStrike_Device_Isolation_Playbook.json</li>
      <li>📄 Cliente_OrchestatorPart_CrowdStrike_Auth_Playbook.json</li>
      <li>📄 Cliente_OrchestatorPart_CrowdStrike_Block_IOC_Playbook.json</li>
      <li>📄 Cliente_Enrich_CrowdStrike_Device_Info_Playbook.json</li>
      <li>📄 Cliente_Enrich_CrowdStrike_Recent_Alerts_Playbook.json</li>
      <li>✅ Deploy_CrowdStrike.json</li>
    </ul>
  </div>

</div>


# Integraciones de Azure Sentinel 🚀

Este repositorio contiene integraciones listas para desplegar en **Azure Sentinel**. Cada integración incluye playbooks de distintos tipos: **Action**, **Enrich**, **Orchestrator**, y el archivo de deploy principal.

---

## Tabla de Integraciones

| Integración | Deploy | Contenido |
|-------------|--------|-----------|
| 🛡️ **Sophos Client Integration** | [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FSophos%2FDeploy_Sophos.json) | ![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Block_Domain_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Block_Hash_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Block_Incident_Domains_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Block_Incident_Hashes_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Block_Incident_IPs_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Block_IP_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Device_Isolation_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_Sophos_Launch_Antivirus_Playbook.json<br>![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) Cliente_OrchestatorPart_Sophos_Block_IOC_Playbook.json<br>![Enrich](https://img.shields.io/badge/Enrich-JSON-green) Cliente_Enrich_Sophos_Get_Device_Info_Playbook.json<br>![Enrich](https://img.shields.io/badge/Enrich-JSON-green) Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook.json<br>✅ Deploy_Sophos.json |
| 🔍 **API Username Parser** | [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FAPI_parser_usernames%2FDeploy_API_Parser.json) | ![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_API_Parser_Account_Entity_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_API_Parser_Alert_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_API_Parser_Incident_Playbook.json<br>![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) Cliente_OrchestatorPart_API_Parser_Playbook.json<br>![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) Cliente_OrchestatorPart_API_Petition.json<br>✅ Deploy_API_Parser.json |
| 🦅 **CrowdStrike Falcon Integration** | [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FCrowdStrike%2FDeploy_CrowdStrike.json) | ![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_CrowdStrike_Block_Hash_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_CrowdStrike_Block_Incident_Hashes_Playbook.json<br>![Action](https://img.shields.io/badge/Action-JSON-blue) Cliente_Action_CrowdStrike_Device_Isolation_Playbook.json<br>![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) Cliente_OrchestatorPart_CrowdStrike_Auth_Playbook.json<br>![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) Cliente_OrchestatorPart_CrowdStrike_Block_IOC_Playbook.json<br>![Enrich](https://img.shields.io/badge/Enrich-JSON-green) Cliente_Enrich_CrowdStrike_Device_Info_Playbook.json<br>![Enrich](https://img.shields.io/badge/Enrich-JSON-green) Cliente_Enrich_CrowdStrike_Recent_Alerts_Playbook.json<br>✅ Deploy_CrowdStrike.json |

---

## Notas

- Los archivos **Action** ejecutan acciones dentro de Sentinel.  
- Los archivos **Enrich** se utilizan para enriquecer datos en los incidentes.  
- Los archivos **Orchestrator** ayudan a automatizar tareas de integración.  
- Los archivos `Deploy_*.json` son templates ARM para desplegar la integración completa en tu tenant de Azure Sentinel.  

---

## Generación automática del README

Este README puede ser generado automáticamente por un **workflow de GitHub Actions** cada vez que se haga un push, manteniendo la información actualizada sobre nuevas integraciones o playbooks añadidos.

---

## Emojis / Badges legend

- 🛡️ Sophos  
- 🔍 API Parser  
- 🦅 CrowdStrike  
- 📄 Playbook Action  
- ✅ Archivo de deploy  
- ![Action](https://img.shields.io/badge/Action-JSON-blue) = Action Playbook  
- ![Enrich](https://img.shields.io/badge/Enrich-JSON-green) = Enrich Playbook  
- ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) = Orchestrator Playbook
