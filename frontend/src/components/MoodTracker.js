import './MoodTracker.css';
import React, { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Line } from "react-chartjs-2";
import axios from 'axios';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const MoodTracker = ({ user }) => {
  const [moodData, setMoodData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMoodData = async () => {
      setIsLoading(true);
      try {
        const token = await user.getIdToken();
        const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/user_sentiments`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        console.log('Raw sentiment data:', response.data);

        // Group and average by date, using local timezone
        const groupedByDate = response.data.reduce((acc, entry) => {
          // Convert UTC date to local timezone and format
          const localDate = new Date(entry.created_at);
          const dateKey = localDate.toLocaleDateString(undefined, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
          });

          if (!acc[dateKey]) {
            acc[dateKey] = {
              total: entry.sentiment_score,
              count: 1,
              date: localDate // Keep full date for sorting
            };
          } else {
            acc[dateKey].total += entry.sentiment_score;
            acc[dateKey].count += 1;
          }
          return acc;
        }, {});

        // Calculate averages and transform for chart
        const transformedData = Object.entries(groupedByDate).map(([date, data]) => ({
          date: date,
          sentiment_score: data.total / data.count,
          originalDate: data.date // Keep for sorting
        }));

        // Sort by date
        transformedData.sort((a, b) => a.originalDate - b.originalDate);

        console.log('Final chart data:', transformedData);
        
        setMoodData(transformedData);
      } catch (error) {
        console.error('Error fetching mood data:', error);
        setError('Failed to load mood data');
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchMoodData();
    }
  }, [user]);

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Your Mood Over Time'
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            return `Mood: ${(context.raw * 100).toFixed(1)}%`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 1,
        title: {
          display: true,
          text: 'Mood Score'
        },
        ticks: {
          callback: (value) => `${(value * 100).toFixed(0)}%`
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date'
        },
        ticks: {
          maxRotation: 45,
          minRotation: 45
        }
      }
    },
    maintainAspectRatio: false
  };

  const chartData = {
    labels: moodData.map((entry) => entry.date),
    datasets: [
      {
        label: "Mood Score",
        data: moodData.map((entry) => entry.sentiment_score),
        fill: true,
        borderColor: "rgb(75, 192, 192)",
        backgroundColor: "rgba(75, 192, 192, 0.2)",
        tension: 0.4,
        pointRadius: 5,
        pointHoverRadius: 7,
      },
    ],
  };

  if (isLoading) return <div className="mood-chart-container">Loading mood data...</div>;
  if (error) return <div className="mood-chart-container">{error}</div>;

  return (
    <div className="mood-chart-container">
      {moodData.length > 0 ? (
        <Line data={chartData} options={options} height={300} />
      ) : (
        <p>No mood data available yet.</p>
      )}
    </div>
  );
};

export default MoodTracker;
