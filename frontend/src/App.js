import React, { useState, useEffect } from "react";
import ChatSidebar from "./components/ChatSidebar";
import ChatWindow from "./components/ChatWindow";
import Login from "./components/Login";
import Logout from "./components/Logout";
import { auth } from "./Firebase";
import { onAuthStateChanged } from "firebase/auth";
import "./styles.css";


const App = () => {

  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);

  // Listen for authentication state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });

    return () => unsubscribe();
  }, []);

  if (!user) {
    return <Login setUser = {setUser}/>;
  }

  return (
    <div className="app-container">
      <header className="header">
        <p>Welcome, {user.displayName} ({user.email})</p>
        <Logout user={user} setUser={setUser} />
      </header>

      {/* FLEX CONTAINER FOR SIDEBAR AND CHAT WINDOW */}
      <div className="app-content">
        <div className="sidebar-container">
          <ChatSidebar
            user={user}
            activeSession={activeSession}
            setActiveSession={setActiveSession}
          />
        </div>
        <div className="chat-window-container">
          <ChatWindow
            user={user}
            activeSession={activeSession}
          />
        </div>  
      </div>
    </div>
  );
};

export default App;