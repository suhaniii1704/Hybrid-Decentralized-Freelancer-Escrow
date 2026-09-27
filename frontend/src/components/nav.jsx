import { Link } from "react-router-dom";
import { Wallet } from "lucide-react";

function Navbar() {
    return (
        <nav className="navbar">
            <Link to="/" className="logo">
                EscrowX
            </Link>

            <div className="nav-links">
                <Link to="/">Home</Link>
                <a href="#how-it-works">How It Works</a>
                <a href="#features">Features</a>
                <a href="#freelancers">For Freelancers</a>
            </div>

            <div className="nav-actions">
                <Link to="/login" className="login-btn">
                    Login
                </Link>

                <button className="wallet-btn">
                    <Wallet size={18} />
                    Connect Wallet
                </button>
            </div>
        </nav>
    );
}

export default Navbar;