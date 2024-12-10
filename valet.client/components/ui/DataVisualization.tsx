import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

interface Props {
  data: string[][];
}

const DataVisualization: React.FC<Props> = ({ data }) => {
  if (!data || data.length === 0) return <div>No data available</div>;

  const [values, labels] = data;
  const chartData = [{
    name: "Cars by Color",
    ...labels.reduce((acc, label, index) => {
      acc[label] = parseInt(values[index]) || 0;
      return acc;
    }, {} as Record<string, number>)
  }];

  const colorPalette = [
    "#ef4444", // Red
    "#3b82f6", // Blue
    "#22c55e", // Green
    "#f97316", // Orange
    "#8b5cf6", // Purple
    "#fbbf24", // Gold
    "#14b8a6", // Teal
    "#ec4899", // Pink
    "#84cc16", // Lime
    "#6366f1"  // Indigo
  ];

  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      <BarChart width={600} height={400} data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        {labels.map((label, index) => (
          <Bar 
            key={label}
            dataKey={label}
            fill={colorPalette[index % colorPalette.length]}
            stroke={label === "White" ? "#374151" : undefined}
          />
        ))}
      </BarChart>
    </div>
  );
};

export default DataVisualization;