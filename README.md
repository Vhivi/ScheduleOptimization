# 📆 Schedule Optimization Project

## 🔬 Overview

📆 Schedule Optimization Project is a 🛠️ tool designed to generate optimized work schedules for a team of 👥 agents. It considers various constraints like ⏳ availability, 🎓 training days, 💖 preferences, and more to create ⚖️ balanced schedules. The project aims to minimize ⚡ scheduling conflicts while maximizing 🤝 fairness and 🚀 efficiency.

---

## ⚠️ Warning

⚠️ This project is specifically designed for generating private security guard schedules, considering the rules and constraints imposed by the French Labour Code.

📌 It is the user's responsibility to ensure that the rules specific to their organization or sector are also respected. This project may require 🛠️ adjustments for other domains or legislative frameworks.

---

## ✨ Key Features

### 📊 Intelligent Scheduling

- 🔄 Generate tailored schedules accommodating agent availability, vacations, and preferences.
- ⚒️ Optimize workloads while adhering to strict and flexible constraints.

### ⚖️ Constraint Management

- **❌ Hard Constraints**: Rules strictly enforced (e.g., no overlapping shifts).
- **💖 Soft Constraints**: Preferences considered for optimization (e.g., preferred shifts).

### 📂 Modular Configuration

- 🔨 Flexible parameters defined through the `config.json` file.
- ✉️ Support for agent preferences, exclusions, and training days.

### 🔧 Visual Interactivity

- 🔍 Vue.js-powered frontend for seamless schedule visualization and interaction.

---

## 🚀 Setup and Usage

### 🛠️ Prerequisites

Ensure the following tools are installed:

- 💻 Python 3.10+
- 📦 Node.js and npm
- 🔐 Git

### 🔄 Installation Steps

1. 🔧 Clone the repository:

   ```bash
   git clone https://github.com/your-username/schedule-optimization.git
   cd schedule-optimization
   ```

2. ✏️ Configure the application:

   - Edit the `config.json` file in the `backend` directory to define agents, shifts, and constraints. Detailed instructions for configuring `config.json` are provided in the Configuration File section below.

3. 🔧 Start the backend server:

   ```bash
   cd backend
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

## 📕 Configuration File (`config.json`)

### 🔬 Structure Overview

Dates in the `config.json` file should be formatted as `dd-mm-YY` for full dates or `dd-mm` for recurring holidays and events.

The `config.json` file serves as the core customization hub:

```json
{
  "agents": [
    {
      "name": "Agent1",
      "preferences": {
        "preferred": ["Jour", "CDP"],
        "avoid": ["Nuit"]
        },
      "unavailable": ["17-11-2024", "07-12-2024"],
      "training": ["19-11-2024"],
      "exclusion": ["25-12-2024"],
      "vacation": {
        "start": "28-10-2024",
        "end": "04-11-2024"
      }
   }
  ],
  "vacations": ["Jour", "Nuit", "CDP"],
  "vacation_durations": {
    "Jour": 12,
    "Nuit": 12,
    "CDP": 5.5,
    "Conge": 7
  },
  "holidays": ["01-01", "25-12"]
}
```

### ✏️ Customizable Parameters

- **👥 Agents**:
  - Define preferences, availability, training days, and vacation periods.
- **⏳ Vacations**:
  - Specify shift types and their durations.
- **🎁 Holidays**:
  - Add public holidays to consider in scheduling.

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

## 🔍 Planned Features and Roadmap

📔 As this is a personal project tailored to meet my current needs, no formal roadmap is planned. However, one potential improvement could be the 🌐 standardization of language throughout the 💻 code and 📝 comments.

---

## 🎉 Contributing

Contributions are welcome! This project thrives on feedback and community input. Here’s how you can contribute:

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

The open-source community for inspiration and examples:

- [Muafira Thasni](https://github.com/MuafiraThasni/Nurse-Scheduling)
- [D-Wave Systems Examples](https://github.com/dwave-examples/nurse-scheduling)

- [https://changelog.com/posts/top-ten-reasons-why-i-wont-use-your-open-source-project](https://changelog.com/posts/top-ten-reasons-why-i-wont-use-your-open-source-project)
- [https://thoughtbot.com/blog/how-to-write-a-great-readme](https://thoughtbot.com/blog/how-to-write-a-great-readme)
- [https://www.makeareadme.com](https://www.makeareadme.com)
- [https://github.com/hackergrrl/art-of-readme](https://github.com/hackergrrl/art-of-readme)
- [https://github.com/hackergrrl/common-readme](https://github.com/hackergrrl/common-readme)
- [https://github.com/RichardLitt/standard-readme](https://github.com/RichardLitt/standard-readme)

And **you**, for exploring or/and contributing to this project!

---

Enjoy scheduling smarter with the Schedule Optimization Project! ✨
