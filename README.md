# Schedule Optimization Project

- [Schedule Optimization Project](#schedule-optimization-project)
  - [Description](#description)
  - [⚠️ Warning ⚠️](#️-warning-️)
  - [Features](#features)
  - [Usage](#usage)
    - [Prerequisites](#prerequisites)
    - [Follow these steps to run the project](#follow-these-steps-to-run-the-project)
  - [Configuration File (`config.json`)](#configuration-file-configjson)
  - [Development](#development)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Adding Constraints](#adding-constraints)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Description

Schedule Optimization Project is a tool designed to generate optimized work schedules for a team of agents. It considers various constraints such as availability, training days, preferences, and more to create balanced schedules. The project aims to minimize scheduling conflicts while maximizing fairness and efficiency.

## ⚠️ Warning ⚠️

This project is specifically designed for the **generation of private security guard schedules**, taking into account the rules and constraints imposed by the **French Labour Code**.

It is the user's responsibility to ensure that the rules specific to their organisation or sector are also respected. This project may require adjustments for other areas or legislative frameworks.

## Features

- **Dynamic Schedule Generation**: Generate work schedules based on input data such as agents, vacations, and availability.
- **Constraint Handling**:
  - Hard Constraints: Rules that must always be respected (e.g., no overlapping vacations).
  - Soft Constraints: Rules that should be respected as much as possible (e.g., preferences for specific shifts).
- **Modular Configuration**:
  - Easily configure agents, shifts, and other parameters through a `config.json` file.
- **Frontend Visualization**:
  - A Vue.js-based interface to visualize and interact with generated schedules.

## Usage

### Prerequisites

Before you start, make sure you have installed the following tools:

- [Python 3.10+](https://www.python.org/)
- [Node.js](https://nodejs.org/)
- [npm](https://www.npmjs.com/)

### Follow these steps to run the project

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/schedule-optimization.git
   cd schedule-optimization
   ```

2. Configure the application:
   - Edit the `config.json` file in the `backend` directory to define agents, shifts, and other parameters. (More details on configuration below.)

3. Run the backend server:

   ```bash
   cd ../backend
   flask run
   ```

4. Run the frontend development server:

   ```bash
   cd ../frontend
   npm run serve
   ```

5. Access the application at [http://localhost:8080](http://localhost:8080).

6. Generate a schedule by clicking the "Generate Schedule" button after choosing the desired date range.

## Configuration File (`config.json`)

The `config.json` file is structured as follows:

```json
{
  "agents": [
    {
      "name": "Agent1",
      "preferences": {
        "preferred": ["Jour"],
        "avoid": ["Nuit"]
      },
      "unavailable": ["2024-01-01"],
      "training": ["2024-01-05"],
      "exclusion": ["25-12-2024"],
      "vacation": {
        "start": "2024-02-01",
        "end": "2024-02-10"
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
  "holidays": [
    "01-01",
    "21-04",
    "01-05",
    "08-05",
    "29-05",
    "09-06",
    "14-07",
    "15-08",
    "01-11",
    "11-11",
    "25-12"
  ]
}
```

## Development

### Backend

The backend is built using Flask and Google OR-Tools. It handles schedule generation based on the constraints defined in `config.json`.

### Frontend

The frontend is developed using Vue.js. It provides a user-friendly interface for viewing and interacting with schedules.

### Adding Constraints

Constraints can be added or modified in the backend `app.py` file under the `generate_planning` function. They are categorized as:

- **Hard Constraints**: Enforced without exceptions.
- **Soft Constraints**: Included in the optimization objective but may not always be satisfied.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- [Google OR-Tools](https://developers.google.com/optimization)
- [Vue.js](https://vuejs.org)
- [Flask](https://flask.palletsprojects.com)

For ideas and inspiration for this project, I would like to thank the following people:

- [Muafira Thasni](https://github.com/MuafiraThasni/Nurse-Scheduling)
- [D-Wave Systems Examples](https://github.com/dwave-examples/nurse-scheduling)

---

Happy Scheduling! 🚀
