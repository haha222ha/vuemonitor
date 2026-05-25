import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js"

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
)

export { ChartJS }

export const chartColors = {
  primary: "#6366f1",
  success: "#059669",
  warning: "#d97706",
  danger: "#dc2626",
  info: "#2563eb",
  purple: "#7c3aed",
  pink: "#ec4899",
  teal: "#0d9488",
}

export const chartColorPalette = [
  chartColors.primary,
  chartColors.success,
  chartColors.warning,
  chartColors.danger,
  chartColors.info,
  chartColors.purple,
  chartColors.pink,
  chartColors.teal,
]

export const defaultChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "bottom" as const,
      labels: {
        padding: 16,
        usePointStyle: true,
        font: { size: 12 },
      },
    },
    tooltip: {
      backgroundColor: "rgba(0,0,0,0.8)",
      padding: 12,
      titleFont: { size: 13 },
      bodyFont: { size: 12 },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 11 } },
    },
    y: {
      grid: { color: "rgba(0,0,0,0.06)" },
      ticks: { font: { size: 11 } },
    },
  },
}

export const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: "65%",
  plugins: {
    legend: {
      position: "bottom" as const,
      labels: {
        padding: 16,
        usePointStyle: true,
        font: { size: 12 },
      },
    },
    tooltip: {
      backgroundColor: "rgba(0,0,0,0.8)",
      padding: 12,
    },
  },
}
