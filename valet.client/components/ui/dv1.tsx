import React, { useState, useEffect, useMemo } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface DataVisualizationProps {
  data: string[][];
  title?: string;
  className?: string;
}

const DataVisualization: React.FC<DataVisualizationProps> = ({ 
  data,
  title = 'Data Visualization',
  className = ''
}) => {
  const [isChartReady, setIsChartReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validData = useMemo(() => {
    try {
      return data.filter(item => 
        Array.isArray(item) && 
        item.length === 2 && 
        !isNaN(parseFloat(item[1]))
      );
    } catch (err) {
      setError('Invalid data format');
      return [];
    }
  }, [data]);

  useEffect(() => {
    if (validData && validData.length > 0) {
      setIsChartReady(true);
      setError(null);
    } else {
      setIsChartReady(false);
      setError('No valid data available');
    }
  }, [validData]);

  const chartData = useMemo(() => ({
    labels: validData.map(item => item[0]),
    datasets: [
      {
        label: 'Value',
        data: validData.map(item => parseFloat(item[1])),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  }), [validData]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: title,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-48 bg-red-50 text-red-500 rounded-lg">
        {error}
      </div>
    );
  }

  if (!isChartReady) {
    return (
      <div className="flex items-center justify-center h-48 bg-gray-50">
        Loading visualization...
      </div>
    );
  }

  return (
    <div className={`h-48 ${className}`}>
      <Bar data={chartData} options={options} />
    </div>
  );
};

export default DataVisualization;