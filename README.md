<h1 align="center">LinkedIn Connection Manager</h1>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img alt="License" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
</p>

<p align="center">
  <strong>Simplify Networking Efforts on LinkedIn with the LinkedIn Connection Manager - a Python-based automation tool.</strong>
</p>

<p align="center">
  <img src="https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Logo.svg.original.svg" alt="LinkedIn Connection Manager" width="400">
</p>

## Overview

LinkedIn Connection Manager is a comprehensive Python project designed to streamline and optimize your LinkedIn networking experience. This repository contains a suite of tools to automate connection requests, track pending invitations, and efficiently manage your professional network.

## Features

- Automate LinkedIn connection requests
- Track and manage pending invitations
- Enhance your LinkedIn presence
- Optimize networking potential
- Build valuable professional connections effortlessly

## Installation

1. Clone this repository:

```bash
git clone https://github.com/RodolfoMRibeiro/LinkedIn-Connection-Manager.git
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Configure `parameters.py`:

   - `linkedin_username` and `linkedin_password`: credenciais usadas no login.
   - `profile_urls`: lista de URLs de perfis que você quer exportar (uma URL por linha).
   - `output_json_path`: caminho do arquivo JSON que receberá o resultado.
   - Ajuste `chrome_binary_path` se o Google Chrome estiver em outro caminho no macOS.
   - Para rodar sem abrir o navegador, defina `headless = True`.

2. Execute o script principal:

```bash
python main.py
```

The script will prompt you for user confirmation before proceeding with automation.

3. O JSON com os perfis será salvo no caminho definido em `output_json_path`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is intended for educational and personal use only. Please comply with LinkedIn's terms of service and be respectful of other users.

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

## Contact

If you have any questions or feedback, feel free to contact me at rodolfomarqribeiro@gmail.com.

---

**Disclaimer**: This project is not affiliated with or endorsed by LinkedIn. Use it responsibly and at your own risk.
