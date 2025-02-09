import React, { useState, useEffect } from "react";
import axios from "axios";

const JournalHistory = () => {
  const [entries, setEntries] = useState([]); // Store journal entries
  const [loading, setLoading] = useState(true); // Loading state for history
  const [error, setError] = useState(null); // Error state
  const [newEntry, setNewEntry] = useState(""); // Input for new journal entry
  const [submitting, setSubmitting] = useState(false); // Loading state for form

  // Fetch journal entries from the backend
  useEffect(() => {
    const fetchEntries = async () => {
      try {
        const response = await axios.get("https://aiapp-tlm7.onrender.com/entries");
        setEntries(response.data); // Save fetched entries to state
      } catch (err) {
        setError("Failed to fetch journal entries. Please try again.");
      } finally {
        setLoading(false); // Stop loading spinner
      }
    };

    fetchEntries();
  }, []);

  // Handle form submission for new entries
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await axios.post("https://aiapp-tlm7.onrender.com/summarize", {
        entry: newEntry,
        max_tokens: 1024,
        temperature: 1.0,
      });

      // Add the new entry to the entries list
      const newEntryData = {
        id: Date.now(), // Temporary ID; replace with real ID from the backend if available
        text: newEntry,
        summary: response.data.summary,
        timestamp: new Date().toISOString(),
      };
      setEntries([newEntryData, ...entries]); // Update state with the new entry
      setNewEntry(""); // Clear the input field
    } catch (err) {
      setError("Failed to add a new journal entry. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1>AI Journal App</h1>

      {/* Form to Add New Entry */}
      <form onSubmit={handleSubmit}>
        <textarea
          value={newEntry}
          onChange={(e) => setNewEntry(e.target.value)}
          placeholder="Write your journal entry here..."
          rows="5"
          cols="50"
        ></textarea>
        <br />
        <button type="submit" disabled={submitting || !newEntry}>
          {submitting ? "Submitting..." : "Add Entry"}
        </button>
      </form>

      {/* Error Messages */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Loading Spinner */}
      {loading && <p>Loading journal history...</p>}

      {/* Display Entries */}
      {!loading && entries.length === 0 && <p>No journal entries found.</p>}
      {!loading && entries.length > 0 && (
        <ul>
          {entries.map((entry) => (
            <li key={entry.id}>
              <p><strong>Entry:</strong> {entry.text}</p>
              <p><strong>Summary:</strong> {entry.summary}</p>
              <small>{new Date(entry.timestamp).toLocaleString()}</small>
              <hr />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default JournalHistory;
