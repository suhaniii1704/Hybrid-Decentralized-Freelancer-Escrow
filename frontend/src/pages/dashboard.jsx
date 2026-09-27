function Dashboard() {
    const user = JSON.parse(localStorage.getItem("user"));

    return (
        <div style={{ padding: "40px" }}>
            <h1>Welcome, {user?.name} 👋</h1>

            <p>Email: {user?.email}</p>
            <p>Role: {user?.role}</p>

            <h2>Dashboard</h2>
        </div>
    );
}

export default Dashboard;