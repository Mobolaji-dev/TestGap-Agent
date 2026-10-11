import { Link } from "react-router-dom";
import "./NotFoundPage.css";

/**
 * 404 page - not found with link back to home
 */
export default function NotFoundPage() {
  return (
    <div className="not-found-page">
      <div className="not-found-container">
        <h1 className="text-display-xl">404</h1>
        <p className="text-body-lg">Page not found</p>
        <Link to="/" className="back-link">
          Go back to Start
        </Link>
      </div>
    </div>
  );
}
