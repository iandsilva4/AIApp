import React, { useState, useEffect } from "react";
import { auth } from "./Firebase";
import JournalHistory from "./components/JournalHistory";
import Login from "./components/Login";

const App = () => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    auth.onAuthStateChanged((currentUser) => {
      setUser(currentUser);
    });
  }, []);

  return (
    <div>
      <h1>Journal AI App</h1>
      {user ? <JournalHistory /> : <Login />}
    </div>
  );
};

export default App;