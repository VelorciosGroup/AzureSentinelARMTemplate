import os

# Ajustar la ruta de trabajo a la raíz del repositorio
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(repo_root)

# Ahora todas las rutas son relativas a la raíz
# Por ejemplo, carpetas de integraciones como 'Sophos', 'CrowdStrike', etc.
folders = [f for f in os.listdir('.') if os.path.isdir(f) and not f.startswith('.')]

# Archivo README
readme_file = "README.md"

# URL del repositorio (cambia por tu usuario/repositorio)
repo_url = "https://github.com/VelorciosGroup/AzureSentinelARMTemplate"

# Rama actual (GitHub Actions la define como GITHUB_REF_NAME)
branch = os.environ.get("GITHUB_REF_NAME", "main")

# Solo carpetas de primer nivel en el repo
folders = [f for f in os.listdir('.') if os.path.isdir(f) and not f.startswith('.')]

with open(readme_file, "w", encoding="utf-8") as f:
    f.write("<table>\n")
    f.write("  <tr>\n    <th>Integración</th>\n    <th>Deploy</th>\n    <th>Contenido</th>\n  </tr>\n\n")

    for folder in sorted(folders):
        files = sorted(os.listdir(folder))
        if not files:
            continue

        # Detectamos archivos deploy
        deploy_files = [file for file in files if file.lower().startswith("deploy")]
        deploy_link = f"{repo_url}/blob/{branch}/{folder}/{deploy_files[0]}" if deploy_files else ""

        # Nombre bonito para la integración (tomamos el nombre de la carpeta capitalizado)
        title = folder.replace('_', ' ').title()

        f.write("  <tr>\n")
        f.write(f"    <td><b>{title}</b></td>\n")
        f.write(f"    <td>\n      <a href=\"{deploy_link}\">Deploy</a>\n    </td>\n")
        f.write("    <td>\n      <ul>\n")
        for file in files:
            file_link = f"{repo_url}/blob/{branch}/{folder}/{file}"
            f.write(f"        <li><a href=\"{file_link}\">{file}</a></li>\n")
        f.write("      </ul>\n")
        f.write("    </td>\n  </tr>\n\n")

    f.write("</table>\n")
