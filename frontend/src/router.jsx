import { createBrowserRouter } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Tours from "./pages/Tours";
import TourDetails from "./pages/TourDetails";
import MyBookings from "./pages/MyBookings";
import ProtectedRoute from "./components/ProtectedRoute";

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },

  {
    path: "/tours",
    element: (
      <ProtectedRoute>
        <Tours />
      </ProtectedRoute>
    ),
  },
  {
    path: "/tours/:id",
    element: (
      <ProtectedRoute>
        <TourDetails />
      </ProtectedRoute>
    ),
  },
  {
    path: "/bookings",
    element: (
      <ProtectedRoute>
        <MyBookings />
      </ProtectedRoute>
    ),
  },

  // дефолт
  { path: "*", element: <Login /> },
]);
