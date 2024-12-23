// components/DataVisualization/index.tsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface DataVisualizationProps {
  data: {
    results?: (string | number)[][];
    columns?: string[];
    explanation?: string;
  };
}

type ChartData = Record<string, string | number>;
type ChartType = 'bar' | 'pie' | 'none';

const COLORS = ['#4F46E5', '#2563EB', '#3B82F6', '#60A5FA', '#93C5FD'];

const DataVisualization: React.FC<DataVisualizationProps> = ({ data }) => {
  const { results, columns } = data;

  if (!results || !columns || results.length === 0 || columns.length === 0) {
    return null;
  }

  const isNumeric = (value: any): boolean => {
    return !isNaN(parseFloat(value)) && isFinite(value);
  };

  const isCountQuery = (): boolean => {
    return (
      columns.length === 1 &&
      columns[0].toLowerCase().includes('count') &&
      results.length === 1 &&
      results[0].length === 1
    );
  };

  if (isCountQuery()) {
    const count = results[0][0];
    const chartData = [{
      name: 'Count',
      value: Number(count)
    }];

    return (
      <div className="max-w-2xl mx-auto">
        <div className="h-64 w-full mt-4">
          <ResponsiveContainer>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar
                dataKey="value"
                fill={COLORS[0]}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  }

  const shouldVisualize = (): boolean => {
    if (results.length === 0) return false;
    if (results[0].length === 0) return false;
    return true;
  };

  const formatChartData = (): ChartData[] => {
    return results.map((row) => {
      const obj: ChartData = {};
      columns.forEach((col, index) => {
        obj[col] = isNumeric(row[index]) ? parseFloat(row[index].toString()) : row[index];
      });
      return obj;
    });
  };

  const determineChartType = (): ChartType => {
    if (!shouldVisualize()) return 'none';

    if (results.length > 1 && columns.length >= 2) {
      return 'bar';
    }

    if (results.length === 1 && columns.length === 2) {
      return 'pie';
    }

    return 'none';
  };

  const renderBarChart = (chartData: ChartData[]) => {
    if (chartData.length === 0) return null;

    const dataKeys = Object.keys(chartData[0]).filter(key => isNumeric(chartData[0][key]));
    const categoryKey = Object.keys(chartData[0]).find(key => !isNumeric(chartData[0][key])) || '';

    return (
      <div className="h-64 w-full mt-4">
        <ResponsiveContainer>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={categoryKey} />
            <YAxis />
            <Tooltip />
            {dataKeys.map((key, index) => (
              <Bar 
                key={key}
                dataKey={key}
                fill={COLORS[index % COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const renderPieChart = (chartData: ChartData[]) => {
    if (chartData.length === 0) return null;

    const valueKey = Object.keys(chartData[0]).find(key => isNumeric(chartData[0][key]));
    const labelKey = Object.keys(chartData[0]).find(key => !isNumeric(chartData[0][key]));

    if (!valueKey || !labelKey) return null;

    return (
      <div className="h-64 w-full mt-4">
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, value }) => `${name}: ${value}`}
              outerRadius={80}
              fill="#8884d8"
              dataKey={valueKey}
              nameKey={labelKey}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  };

  if (!shouldVisualize()) {
    return null;
  }

  const chartData = formatChartData();
  const chartType = determineChartType();

  return (
    <div className="max-w-2xl mx-auto">
      {chartType === 'bar' && renderBarChart(chartData)}
      {chartType === 'pie' && renderPieChart(chartData)}
    </div>
  );
};

export default DataVisualization;