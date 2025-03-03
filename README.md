# Project Betas

Project Betas is a multi-stack application designed to analyze market data and calculate beta values for different assets. The project integrates components written in both Python and JavaScript, providing a robust backend for data processing along with a dynamic frontend for visualization.

## Stack & Technologies

- **Backend (Python):**
  - The core analytical functionalities are implemented in Python.
  - Python scripts (e.g., `main.py`, `src/beta_calculator.py`, `src/data_fetcher.py`) handle data fetching, beta calculations, and market analysis.
  - The [requirements.txt](requirements.txt) file lists the external Python libraries needed. Typical libraries might include:
    - `requests` for HTTP operations,
    - `numpy` and `pandas` for numerical analysis and data manipulation,
    - Other specialized libraries as required by the analysis.

- **Frontend (JavaScript/React):**
  - The user interface is developed using React.
  - Components found in `src/` such as `src/App.js`, `src/components/BetaPatternAnalysis.js`, and `src/components/MarketBetaAnalysis.js` contribute to a responsive UI.
  - State management is handled through the use of atoms in `src/atoms/marketBetaState.js` (commonly achieved using libraries like Recoil).

## Libraries & Tools

The project utilizes a range of libraries to streamline data processing and UI interactivity:

- **Python Libraries:**
  - Libraries such as `ccxt`, `requests`, `numpy`, and `pandas` enable efficient data handling, computation, and network operations.
  - Additional libraries include `streamlit`, `plotly`, and `matplotlib` for interactive visualizations and app development.
  - All required packages are listed in the [requirements.txt](requirements.txt) file.

- **JavaScript Libraries:**
  - **React:** For building the user interface and creating interactive components.
  - **State Management (e.g., Recoil):** Helps manage and share state across different components.
  - Additional packages for styling, data fetching, or charting may also be integrated into the React stack.
