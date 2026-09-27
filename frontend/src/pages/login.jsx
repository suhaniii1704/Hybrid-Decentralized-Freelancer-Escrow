import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock } from "lucide-react";

function Login() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        email: "",
        password: ""
    });

    const [message, setMessage] = useState("");

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const response = await fetch(
                "http://localhost:5000/api/auth/login",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(formData)
                }
            );

            const data = await response.json();

            if (!response.ok) {
                setMessage(data.message);
                return;
            }

            // Save JWT token
            localStorage.setItem("token", data.token);

            // Save user information
            localStorage.setItem("user", JSON.stringify(data.user));

            setMessage("Login successful!");

            // Go to dashboard
            setTimeout(() => {
                navigate("/dashboard");
            }, 500);

        } catch (error) {
            console.error("Login Error:", error);
            setMessage("Unable to connect to server");
        }
    };

    return (
        <div className="auth-page">

            <div className="auth-card">

                <div className="auth-header">
                    <h1>Welcome back</h1>
                    <p>Login to your EscrowX account</p>
                </div>

                <form onSubmit={handleSubmit}>

                    <div className="input-group">
                        <label>Email</label>

                        <div className="input-wrapper">
                            <Mail size={18} />

                            <input
                                type="email"
                                name="email"
                                placeholder="Enter your email"
                                value={formData.email}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <label>Password</label>

                        <div className="input-wrapper">
                            <Lock size={18} />

                            <input
                                type="password"
                                name="password"
                                placeholder="Enter your password"
                                value={formData.password}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <button type="submit" className="auth-btn">
                        Login
                    </button>

                </form>

                {message && (
                    <p style={{ textAlign: "center", marginTop: "15px" }}>
                        {message}
                    </p>
                )}

                <p className="auth-footer">
                    Don't have an account?
                    <Link to="/signup"> Create Account</Link>
                </p>

            </div>

        </div>
    );
}

export default Login;