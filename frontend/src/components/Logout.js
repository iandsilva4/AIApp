import React from "react";
import { auth } from "../Firebase";
import { signOut } from "firebase/auth";
import "./Logout.css"; // New separate CSS file for logout styling

const Logout = ({ user, setUser }) => {
  const handleLogout = async () => {
    try {
      await signOut(auth);
      setUser(null);
      localStorage.removeItem("user");
    } catch (error) {
      console.error("Error logging out:", error.message);
    }
  };

  return (
    <div className="logout-container">
      <button className="logout-button" onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
};

export default Logout;
