import React, { useState } from "react";
import axios from "axios";

const JournalForm = () => {
  const [entry, setEntry] = useState(""); // User input
  const [summary, setSummary] = useState(""); // Summary from backend
  const [loading, setLoading] = useState(false); // Loading state
  const [error, setError] = useState(null); // Error state

  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent page reload
    setLoading(true);
    setError(null);
    setSummary(""); // Reset previous results

    try {
      // Send POST request to backend
      const response = await axios.post("https://aiapp-tlm7.onrender.com/summarize", {
        entry: entry,
        max_tokens: 1024,
        temperature: 1.0,
      });

      // Update the summary with the response
      setSummary(response.data.summary);
    } catch (err) {
      // Handle errors
      setError("An error occurred while summarizing. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Journal Summarizer</h1>
      <form onSubmit={handleSubmit}>
        <textarea
          value={entry}
          onChange={(e) => setEntry(e.target.value)}
          placeholder="Write your journal entry here..."
          rows="10"
          cols="50"
        ></textarea>
        <br />
        <button type="submit" disabled={loading}>
          {loading ? "Summarizing..." : "Submit"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {summary && (
        <div>
          <h2>Summary:</h2>
          <p>{summary}</p>
        </div>
      )}
    </div>
  );
};

export default JournalForm;
