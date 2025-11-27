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



# Azure Sentinel Integrations 🚀

Este repositorio contiene integraciones listas para desplegar en **Azure Sentinel**.  
Cada integración incluye playbooks de distintos tipos: **Action**, **Enrich**, **Orchestrator**, y su archivo de deploy.

| Integración | Deploy | Playbook | Tipo |
|-------------|--------|----------|------|
| 🛡️ Sophos Client Integration | [![Deploy](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FSophos%2FDeploy_Sophos.json) | Cliente_Action_Sophos_Block_Domain_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Block_Hash_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Block_Incident_Domains_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Block_Incident_Hashes_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Block_Incident_IPs_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Block_IP_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Device_Isolation_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_Sophos_Launch_Antivirus_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_OrchestatorPart_Sophos_Block_IOC_Playbook.json | ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) |
| | | Cliente_Enrich_Sophos_Get_Device_Info_Playbook.json | ![Enrich](https://img.shields.io/badge/Enrich-JSON-green) |
| | | Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook.json | ![Enrich](https://img.shields.io/badge/Enrich-JSON-green) |
| | | Deploy_Sophos.json | ✅ Deploy |

| 🔍 API Username Parser | [![Deploy](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FAPI_parser_usernames%2FDeploy_API_Parser.json) | Cliente_Action_API_Parser_Account_Entity_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_API_Parser_Alert_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_API_Parser_Incident_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_OrchestatorPart_API_Parser_Playbook.json | ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) |
| | | Cliente_OrchestatorPart_API_Petition.json | ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) |
| | | Deploy_API_Parser.json | ✅ Deploy |

| 🦅 CrowdStrike Falcon Integration | [![Deploy](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVelorciosGroup%2FAzureSentinelARMTemplate%2Frefs%2Fheads%2Fmain%2FCrowdStrike%2FDeploy_CrowdStrike.json) | Cliente_Action_CrowdStrike_Block_Hash_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_CrowdStrike_Block_Incident_Hashes_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_Action_CrowdStrike_Device_Isolation_Playbook.json | ![Action](https://img.shields.io/badge/Action-JSON-blue) |
| | | Cliente_OrchestatorPart_CrowdStrike_Auth_Playbook.json | ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) |
| | | Cliente_OrchestatorPart_CrowdStrike_Block_IOC_Playbook.json | ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) |
| | | Cliente_Enrich_CrowdStrike_Device_Info_Playbook.json | ![Enrich](https://img.shields.io/badge/Enrich-JSON-green) |
| | | Cliente_Enrich_CrowdStrike_Recent_Alerts_Playbook.json | ![Enrich](https://img.shields.io/badge/Enrich-JSON-green) |
| | | Deploy_CrowdStrike.json | ✅ Deploy |

---

### 📌 Notas

- Los archivos **Action** ejecutan acciones dentro de Sentinel.  
- Los archivos **Enrich** se utilizan para enriquecer datos en los incidentes.  
- Los archivos **Orchestrator** ayudan a automatizar tareas de integración.  
- Los archivos `Deploy_*.json` son templates ARM para desplegar la integración completa en tu tenant de Azure Sentinel.  

---

### 🎨 Leyenda

- 🛡️ Sophos  
- 🔍 API Parser  
- 🦅 CrowdStrike  
- ![Action](https://img.shields.io/badge/Action-JSON-blue) = Action Playbook  
- ![Enrich](https://img.shields.io/badge/Enrich-JSON-green) = Enrich Playbook  
- ![Orchestrator](https://img.shields.io/badge/Orchestrator-JSON-purple) = Orchestrator Playbook  
- ✅ Deploy

