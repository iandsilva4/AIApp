import React from "react";
import { auth } from "../Firebase";
import { signOut } from "firebase/auth";
import "./Logout.css"; // New separate CSS file for logout styling
import { ReactComponent as LogoutIcon } from '../assets/logout-icon.svg';

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
      <button className="icon-button" onClick={handleLogout} title="Logout">
        <LogoutIcon />
      </button>
    </div>
  );
};

export default Logout;