import React from "react";
import NavBar from "./components/NavBar";
import "./App.css";
import "./styles/Global.css";
import About from "./components/About";
import Dashboard from "./components/Dashboard";

function App() {
  return (
    <div className="App">
      <NavBar></NavBar>
      <div id="content">
        <Dashboard></Dashboard>
        <About></About>  

      </div>
    </div>
  );
}

export default App;
