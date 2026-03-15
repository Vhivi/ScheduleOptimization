# 📆 Schedule Optimization Project

## 🔬 Overview

📆 Schedule Optimization Project is a tool designed to generate optimized work schedules for a team of agents. It considers various constraints like availability, training days, preferences, and more like **multiple leave periods** to create balanced schedules. The project aims to minimize scheduling conflicts while maximizing fairness and efficiency.

---

## ⚠️ Warning

⚠️ This project is specifically designed for generating private security guard schedules, considering the rules and constraints imposed by the French Labour Code.

📌 It is the user's responsibility to ensure that the rules specific to their organization or sector are also respected. This project may require 🛠️ adjustments for other domains or legislative frameworks.

---

## ✨ Key Features

### 📊 Intelligent Scheduling

- 🔄 Generate tailored schedules accommodating agent availability, leaves, and preferences.
- ⚒️ Optimize workloads while adhering to strict and flexible constraints.

### ⚖️ Constraint Management

- **❌ Hard Constraints**: Rules strictly enforced (e.g., no overlapping shifts).
- **💖 Soft Constraints**: Preferences considered for optimization (e.g., preferred shifts).

### 📂 Modular Configuration

- 🔨 Flexible parameters defined through the `config.json` file.
- ✉️ Support for agent preferences, exclusions, training days, and **multiple leave periods**.

### 🔧 Visual Interactivity

- 🔍 Vue.js-powered frontend for seamless schedule visualization and interaction.

---

## 🚀 Setup and Usage

### 🛠️ Prerequisites

Ensure the following tools are installed:

- 💻 Python 3.10+
- 📦 Node.js and npm
- 📦 Flask
- 🔐 Git

### 🔄 Installation Steps

1. 🔧 Clone the repository:

   ```bash
   git clone https://github.com/Vhivi/ScheduleOptimization.git
   cd ScheduleOptimization
   ```

2. ✏️ Configure the application:

   - Edit the `backend/config.json` file to define agents, shifts, and constraints. Detailed instructions for configuring `config.json` are provided in the Configuration File section below.

3. 🔧 Setup and run the backend (recommended with a virtual environment):

   ```bash
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   python -m pytest -q
   flask run
   ```

4. 🎩 Launch the frontend server:

   Note: The `npm install` step is mandatory only during the initial setup or when new dependencies are added. You can skip this step during subsequent launches if no changes have been made to the dependencies.

   ```bash
   cd frontend
   npm install
   npm run serve
   ```

5. 🔍 Access the application at `http://localhost:8080` and start scheduling!

---

## ✅ Testing

Run tests before opening a pull request:

### Backend (Python 3.10 virtual environment)

```bash
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

### Frontend

```bash
cd frontend
npm test -- --runInBand
```

---

## 📕 Configuration File (`config.json`)

Use these files together:

- Reference guide: `docs/config-reference.md`
- JSON schema: `backend/config.schema.json`
- Ready-to-copy example: `backend/config.example.json`

Important date formats:

- Full dates: `dd-mm-YYYY`
- Recurring holidays: `dd-mm`

Core sections in `config.json`:

- `agents`: people and individual constraints (preferences, unavailable dates, training, exclusions, leave periods)
- `vacations`: generated shift types (`Jour`, `Nuit`, `CDP`)
- `vacation_durations`: paid-hour durations for each shift plus `Conge`
- `holidays`: recurring public holidays
- `solver`: optional runtime and fairness tuning

---

## 💡 Development Workflow

### 🔧 Backend

- Powered by Flask and Google OR-Tools.
- Modular structure for adding constraints via the `generate_planning` function.

### 🎩 Frontend

- Built with Vue.js for a dynamic user experience.
- Includes filters, customization options, and hot reloading for rapid development.

### 🕵 Adding Constraints

1. ✏️ Modify the `generate_planning` function in `app.py`.
2. 🔧 Check that your constraint is well integrated and produces the desired effects.
3. ✉️ Update documentation and configuration as needed.

---

## 🧰 Maintenance Policy

- Keep dependency updates incremental and low risk by default (minor and patch versions first).
- Run backend and frontend tests for each dependency update batch.
- Use `npm audit fix` without `--force` in regular maintenance batches.
- Handle breaking updates (for example major Jest/jsdom upgrades) in dedicated pull requests.
- Keep `CHANGELOG.md` updated under `Unreleased` for each maintenance batch.

---

## 🔍 Planned Features and Roadmap

📔 As this is a personal project tailored to meet my current needs, no formal roadmap is planned. However, one potential improvement could be the standardization of language throughout the code and comments.

---

## 🎉 Contributing

Contributions are welcome! This project thrives on feedback and community input.

Before contributing, please take a look at our [ARCHITECTURE.md](ARCHITECTURE.md) file to understand the project's architecture and design decisions.

Here’s how you can contribute:

1. **Fork the Repository**: Create a copy of the project under your GitHub account.

2. **Make Your Changes**: Work on the improvements you’d like to add. Be sure to follow the project’s coding style and guidelines.

3. **Submit a Pull Request**: Propose your changes by creating a pull request. Provide a clear description of your updates and the problem they solve.

### Areas to Contribute

- **Bug Fixes**: Identify and resolve issues in the existing code.
- **Feature Enhancements**: Add new functionalities or optimize existing ones.
- **Documentation Improvements**: Enhance clarity, fix errors, or update outdated content.
- **Code Standardization**: Help in uniformizing the language and comments in the codebase.

Contributions of all kinds are appreciated, and we’re here to support you throughout the process!

---

## 📢 License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## 🌈 Acknowledgments

Special thanks to the following:

- [Google OR-Tools](https://developers.google.com/optimization)
- [Vue.js](https://vuejs.org)
- [Flask](https://flask.palletsprojects.com)
- [Mermaid](https://github.com/mermaid-js/mermaid) for diagramming support in Architecture.md

The open-source community for inspiration and examples:

- [Muafira Thasni - Nurse Scheduling](https://github.com/MuafiraThasni/Nurse-Scheduling)
- [D-Wave Systems Examples - Nurse Scheduling](https://github.com/dwave-examples/nurse-scheduling)

- [https://changelog.com/posts/top-ten-reasons-why-i-wont-use-your-open-source-project](https://changelog.com/posts/top-ten-reasons-why-i-wont-use-your-open-source-project)
- [https://thoughtbot.com/blog/how-to-write-a-great-readme](https://thoughtbot.com/blog/how-to-write-a-great-readme)
- [https://www.makeareadme.com](https://www.makeareadme.com)
- [https://github.com/hackergrrl/art-of-readme](https://github.com/hackergrrl/art-of-readme)
- [https://github.com/hackergrrl/common-readme](https://github.com/hackergrrl/common-readme)
- [https://github.com/RichardLitt/standard-readme](https://github.com/RichardLitt/standard-readme)

And **you**, for exploring or/and contributing to this project!

---

Enjoy scheduling smarter with the Schedule Optimization Project! ✨
