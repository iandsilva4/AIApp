import React, { useEffect } from "react";
import { signInWithGoogle, auth } from "../Firebase";
import { onAuthStateChanged } from "firebase/auth";
import "./Login.css";
import { FaGoogle } from "react-icons/fa";

const Login = ({ setUser }) => {

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        setUser(user);
        localStorage.setItem("user", JSON.stringify(user));
      } else {
        setUser(null);
        localStorage.removeItem("user");
      }
    });

    return () => unsubscribe();
  }, [setUser]);

  const handleLogin = async () => {
    const loggedInUser = await signInWithGoogle();
    if (loggedInUser) {
      setUser(loggedInUser);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h2>Log in</h2>
        <button className="google-login-button" onClick={handleLogin}>
          <FaGoogle className="google-icon" /> Continue with Google
        </button>
      </div>
    </div>
  );
};

export default Login;


/*
return (
    <div className="login-page">
      {user ? (
        <div className="login-card">
          <p className="welcome-text">Welcome, {user.displayName}</p>
          <button className="logout-button" onClick={handleLogout}>Logout</button>
        </div>
      ) : (
        <div className="login-card">
          <h2>Log in</h2>
          <button className="google-login-button" onClick={handleLogin}>
            <FaGoogle className="google-icon" /> Continue with Google
          </button>

          <div className="divider"><span>or</span></div>

          <div className="input-container">
            <input type="email" placeholder="Email" className="input-field" />
          </div>

          <div className="input-container">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              className="input-field"
            />
            <span
              className="password-toggle"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FaRegEyeSlash /> : <FaRegEye />}
            </span>
          </div>

          <div className="forgot-password">
            <a href="#">Forgot Password?</a>
          </div>

          <button className="login-button">Log in</button>

          <p className="signup-text">
            New user? <a href="#">Sign up</a>
          </p>
        </div>
      )}
    </div>
  );
};
*/