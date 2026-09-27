import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { User, Mail, Lock } from "lucide-react";

function Signup() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        name: "",
        email: "",
        password: "",
        confirmPassword: "",
        role: ""
    });

    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        setMessage("");
        setLoading(true);

        try {
            const response = await fetch(
                "http://localhost:5000/api/auth/signup",
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

            setMessage("Account created successfully!");

            setTimeout(() => {
                navigate("/login");
            }, 1000);

        } catch (error) {
            console.error(error);
            setMessage("Unable to connect to server");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">

                <div className="auth-header">
                    <h1>Create your account</h1>
                    <p>Join the decentralized freelance ecosystem</p>
                </div>

                <form onSubmit={handleSubmit}>

                    <div className="input-group">
                        <label>Full Name</label>

                        <div className="input-wrapper">
                            <User size={18} />

                            <input
                                type="text"
                                name="name"
                                placeholder="Enter your name"
                                value={formData.name}
                                onChange={handleChange}
                            />
                        </div>
                    </div>

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
                                placeholder="Create a password"
                                value={formData.password}
                                onChange={handleChange}
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <label>Confirm Password</label>

                        <div className="input-wrapper">
                            <Lock size={18} />

                            <input
                                type="password"
                                name="confirmPassword"
                                placeholder="Confirm your password"
                                value={formData.confirmPassword}
                                onChange={handleChange}
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <label>I want to join as</label>

                        <div className="role-selection">

                            <label className="role-option">
                                <input
                                    type="radio"
                                    name="role"
                                    value="client"
                                    checked={formData.role === "client"}
                                    onChange={handleChange}
                                />

                                <div>
                                    <strong>Client</strong>
                                    <span>Hire freelancers</span>
                                </div>
                            </label>

                            <label className="role-option">
                                <input
                                    type="radio"
                                    name="role"
                                    value="freelancer"
                                    checked={formData.role === "freelancer"}
                                    onChange={handleChange}
                                />

                                <div>
                                    <strong>Freelancer</strong>
                                    <span>Find projects</span>
                                </div>
                            </label>

                        </div>
                    </div>

                    <button
                        type="submit"
                        className="auth-btn"
                        disabled={loading}
                    >
                        {loading ? "Creating Account..." : "Create Account"}
                    </button>

                    {message && (
                        <p style={{ marginTop: "15px", textAlign: "center" }}>
                            {message}
                        </p>
                    )}

                </form>

                <p className="auth-footer">
                    Already have an account?
                    <Link to="/login"> Login</Link>
                </p>

            </div>
        </div>
    );
}

export default Signup;