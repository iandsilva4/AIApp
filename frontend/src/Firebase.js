import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithRedirect, getRedirectResult, signOut, setPersistence, browserLocalPersistence } from "firebase/auth";

// Your Firebase configuration
const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  measurementId: process.env.REACT_APP_FIREBASE_MEASUREMENT_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Set persistence to LOCAL
setPersistence(auth, browserLocalPersistence)
  .catch((error) => {
    console.error("Error setting persistence:", error);
  });

// Get the current URL for redirect
const getRedirectUrl = () => {
  // Use environment variable if set, otherwise use current origin
  return process.env.REACT_APP_AUTH_REDIRECT_URL || window.location.origin;
};

// Configure Google provider with dynamic redirect URI
const getProvider = () => {
  const provider = new GoogleAuthProvider();
  const redirectUrl = getRedirectUrl();
  provider.setCustomParameters({
    prompt: 'select_account',
    redirect_uri: redirectUrl
  });
  return provider;
};

// Authentication functions
export const signInWithGoogle = async (isMobile = false) => {
  try {
    const provider = getProvider();
    const redirectUrl = getRedirectUrl();
    console.log('Using redirect URL:', redirectUrl);

    if (isMobile) {
      console.log('Attempting mobile sign-in with redirect...');
      await getRedirectResult(auth); // Clear any existing redirect result
      await signInWithRedirect(auth, provider);
      return null;
    } else {
      console.log('Attempting desktop sign-in with popup...');
      const result = await signInWithPopup(auth, provider);
      return result.user;
    }
  } catch (error) {
    console.error("Error during sign in:", error.code, error.message);
    if (error.code === 'auth/popup-blocked') {
      throw new Error('Popup was blocked. Please allow popups and try again.');
    }
    throw error;
  }
};

export const getGoogleRedirectResult = async () => {
  try {
    console.log('Checking for redirect result...', window.location.href);
    const result = await getRedirectResult(auth);
    if (result) {
      console.log('Got redirect result:', result.user.email);
      return result.user;
    } else {
      console.log('No redirect result found');
      const currentUser = auth.currentUser;
      if (currentUser) {
        console.log('Found user in auth state:', currentUser.email);
        return currentUser;
      }
      return null;
    }
  } catch (error) {
    console.error("Error getting redirect result:", error.code, error.message, window.location.href);
    throw error;
  }
};

export const logout = async () => {
  try {
    await signOut(auth);
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
  } catch (error) {
    console.error("Error during logout:", error);
    throw error;
  }
};
