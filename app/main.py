from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import os
import aiohttp
from dotenv import load_dotenv
from urllib.parse import quote, urlencode
from typing import List, Optional, Dict
from enum import Enum
from starlette.responses import Response
import logging
from fastapi import status
import glob
import markdown
from pathlib import Path
import discord
from discord import ui
from discord.ext import commands
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Discord configuration
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback").rstrip('/')
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize FastAPI
app = FastAPI(title="VFX Studio Discord App")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://discord.com", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Mount static files from the static directory relative to the script
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Add this middleware after your CORS middleware
@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    response = await call_next(request)
    if isinstance(response, HTMLResponse):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Test endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VFX Pipeline Hub</title>
        <!-- Add Chart.js for beautiful graphs -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <!-- Add modern icons -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            :root {
                --primary: #ffffff;
                --secondary: #e2e2e2;
                --accent: #000000;
                --background: #ffffff;
                --card-bg: #f8f9fa;
                --text: #000000;
                --text-secondary: #666666;
                --success: #00c853;
                --warning: #ffd600;
                --error: #ff1744;
                --shadow: rgba(0, 0, 0, 0.1);
            }

            [data-theme="dark"] {
                --primary: #000000;
                --secondary: #333333;
                --accent: #ffffff;
                --background: #121212;
                --card-bg: #1e1e1e;
                --text: #ffffff;
                --text-secondary: #999999;
                --shadow: rgba(255, 255, 255, 0.1);
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                transition: background-color 0.3s, color 0.3s;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background-color: var(--background);
                color: var(--text);
                line-height: 1.6;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }

            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 0;
                margin-bottom: 40px;
                border-bottom: 1px solid var(--secondary);
            }

            .theme-toggle {
                background: none;
                border: none;
                color: var(--text);
                cursor: pointer;
                font-size: 1.5rem;
                padding: 10px;
            }

            .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 24px;
                margin-bottom: 40px;
            }

            .card {
                background: var(--card-bg);
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 4px 6px var(--shadow);
            }

            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }

            .card h2 {
                font-size: 1.2rem;
                font-weight: 600;
                color: var(--text);
            }

            .status {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
                color: var(--text-secondary);
            }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }

            .status-dot.active { background-color: var(--success); }
            .status-dot.warning { background-color: var(--warning); }
            .status-dot.error { background-color: var(--error); }

            .metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 16px;
            }

            .metric {
                text-align: center;
                padding: 16px;
                background: var(--background);
                border-radius: 8px;
            }

            .metric-value {
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 4px;
            }

            .metric-label {
                font-size: 0.8rem;
                color: var(--text-secondary);
            }

            .timeline {
                margin-top: 16px;
            }

            .timeline-item {
                display: flex;
                gap: 12px;
                padding: 12px 0;
                border-bottom: 1px solid var(--secondary);
            }

            .timeline-icon {
                width: 32px;
                height: 32px;
                background: var(--accent);
                color: var(--background);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .timeline-content {
                flex: 1;
            }

            .timeline-title {
                font-weight: 600;
            }

            .timeline-time {
                font-size: 0.8rem;
                color: var(--text-secondary);
            }

            .progress-bar {
                height: 8px;
                background: var(--secondary);
                border-radius: 4px;
                margin-top: 8px;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                background: var(--accent);
                width: 75%;
                transition: width 0.3s ease;
            }

            .chart-container {
                height: 200px;
                margin-top: 20px;
            }

            .badge {
                background: var(--accent);
                color: var(--background);
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
            }

            .connect-button {
                background: var(--accent);
                color: var(--background);
                padding: 12px 24px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: transform 0.2s;
            }

            .connect-button:hover {
                transform: translateY(-2px);
            }

            @media (max-width: 768px) {
                .dashboard {
                    grid-template-columns: 1fr;
                }
            }

            .logo {
                height: 40px;
                width: auto;
                margin-right: 16px;
            }
            
            .header-content {
                display: flex;
                align-items: center;
            }
            
            .logo-dark {
                display: none;
            }
            
            [data-theme="dark"] .logo-light {
                display: none;
            }
            
            [data-theme="dark"] .logo-dark {
                display: block;
            }

            .header-actions {
                display: flex;
                align-items: center;
                gap: 16px;
            }
            
            .github-button {
                background: var(--accent);
                color: var(--background);
                padding: 8px 16px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s ease;
            }
            
            .github-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px var(--shadow);
            }
            
            .header-content {
                display: flex;
                align-items: center;
            }
            
            .logo {
                height: 40px;
                width: auto;
                margin-right: 16px;
                transition: transform 0.3s ease;
            }
            
            .logo:hover {
                transform: scale(1.05);
            }
            
            .logo-dark {
                display: none;
            }
            
            [data-theme="dark"] .logo-light {
                display: none;
            }
            
            [data-theme="dark"] .logo-dark {
                display: block;
            }
            
            @media (max-width: 768px) {
                .header {
                    flex-direction: column;
                    gap: 20px;
                    text-align: center;
                }
                
                .header-actions {
                    flex-direction: column;
                    width: 100%;
                }
                
                .github-button, .connect-button {
                    width: 100%;
                    justify-content: center;
                }
            }

            /* Ticket Styles */
            .create-ticket-btn {
                background: var(--accent);
                color: var(--background);
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
                transition: transform 0.2s;
            }

            .create-ticket-btn:hover {
                transform: translateY(-2px);
            }

            .tickets-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
                max-height: 400px;
                overflow-y: auto;
                padding: 12px 0;
            }

            .ticket-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: var(--background);
                border-radius: 8px;
                transition: transform 0.2s;
                border: 1px solid var(--secondary);
            }

            .ticket-item:hover {
                transform: translateX(4px);
            }

            .ticket-info {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }

            .ticket-title {
                font-weight: 600;
            }

            .ticket-meta {
                font-size: 0.8rem;
                color: var(--text-secondary);
            }

            .ticket-status {
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 500;
            }

            .status-open { 
                background: var(--warning);
                color: var(--text);
            }

            .status-in-progress { 
                background: var(--accent);
                color: var(--background);
            }

            .status-resolved { 
                background: var(--success);
                color: var(--background);
            }

            .loading-message {
                text-align: center;
                color: var(--text-secondary);
                padding: 20px;
            }

            .error-message {
                text-align: center;
                color: var(--error);
                padding: 20px;
                background: rgba(var(--error-rgb), 0.1);
                border-radius: 8px;
            }

            /* Modal Styles */
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                z-index: 1000;
            }

            .modal-content {
                position: relative;
                background: var(--background);
                margin: 10% auto;
                padding: 24px;
                width: 90%;
                max-width: 600px;
                border-radius: 12px;
                box-shadow: 0 4px 20px var(--shadow);
            }

            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }

            .close-btn {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: var(--text);
            }

            .form-group {
                margin-bottom: 16px;
            }

            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }

            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: var(--text);
            }

            .form-group input,
            .form-group select,
            .form-group textarea {
                width: 100%;
                padding: 8px;
                border: 1px solid var(--secondary);
                border-radius: 4px;
                background: var(--background);
                color: var(--text);
            }

            .form-group textarea {
                min-height: 100px;
                resize: vertical;
            }

            .form-actions {
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                margin-top: 24px;
            }

            .submit-btn,
            .cancel-btn {
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
                cursor: pointer;
                font-weight: 500;
            }

            .submit-btn {
                background: var(--accent);
                color: var(--background);
            }

            .cancel-btn {
                background: var(--secondary);
                color: var(--text);
            }

            .old-tickets-list {
                max-height: 500px;
                overflow-y: auto;
            }

            .ticket-content {
                padding: 20px;
                max-height: 70vh;
                overflow-y: auto;
                background: var(--card-bg);
                border-radius: 8px;
                margin-top: 16px;
            }

            .view-ticket-btn {
                background: var(--accent);
                color: var(--background);
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: transform 0.2s;
            }

            .view-ticket-btn:hover {
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header class="header">
                <div class="header-content">
                    <a href="/" class="logo-link">
                        <img src="https://raw.githubusercontent.com/Themolx/Incognito/c0dd02b21ef30b9e5f9223c2046739406bc3e032/assets/black.png" 
                             alt="Logo Light" 
                             class="logo logo-light">
                        <img src="https://raw.githubusercontent.com/Themolx/Incognito/c0dd02b21ef30b9e5f9223c2046739406bc3e032/assets/white.png" 
                             alt="Logo Dark" 
                             class="logo logo-dark">
                    </a>
                    <div>
                        <h1>VFX Pipeline Hub</h1>
                        <p>Real-time pipeline monitoring & management</p>
                    </div>
                </div>
                <div class="header-actions">
                    <button class="theme-toggle" onclick="toggleTheme()">
                        <i class="fas fa-moon"></i>
                    </button>
                    <a href="https://github.com/Themolx/Incognito" 
                       target="_blank" 
                       rel="noopener noreferrer" 
                       class="github-button">
                        <i class="fab fa-github"></i>
                        GitHub
                    </a>
                    <a href="/auth/login" class="connect-button">
                        <i class="fab fa-discord"></i>
                        Connect Discord
                    </a>
                </div>
            </header>

            <div class="dashboard">
                <!-- Render Farm Status -->
                <div class="card">
                    <div class="card-header">
                        <h2>Render Farm Status</h2>
                        <div class="status">
                            <span class="status-dot active"></span>
                            Online
                        </div>
                    </div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">42</div>
                            <div class="metric-label">Active Nodes</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">87%</div>
                            <div class="metric-label">CPU Usage</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">23</div>
                            <div class="metric-label">Queue Size</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="farmUsageChart"></canvas>
                    </div>
                </div>

                <!-- Project Status -->
                <div class="card">
                    <div class="card-header">
                        <h2>Active Projects</h2>
                        <div class="status">
                            <span class="status-dot active"></span>
                            3 Projects
                        </div>
                    </div>
                    <div class="timeline">
                        <div class="timeline-item">
                            <div class="timeline-icon">
                                <i class="fas fa-film"></i>
                            </div>
                            <div class="timeline-content">
                                <div class="timeline-title">Project Alpha</div>
                                <div class="timeline-time">Deadline: 2024-04-15</div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 75%"></div>
                                </div>
                            </div>
                            <div class="badge">In Progress</div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-icon">
                                <i class="fas fa-tv"></i>
                            </div>
                            <div class="timeline-content">
                                <div class="timeline-title">Project Beta</div>
                                <div class="timeline-time">Deadline: 2024-05-01</div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 45%"></div>
                                </div>
                            </div>
                            <div class="badge">Review</div>
                        </div>
                    </div>
                </div>

                <!-- Resource Monitor -->
                <div class="card">
                    <div class="card-header">
                        <h2>Resource Monitor</h2>
                        <div class="status">
                            <span class="status-dot warning"></span>
                            High Usage
                        </div>
                    </div>
                    <div class="chart-container">
                        <canvas id="resourceChart"></canvas>
                    </div>
                </div>

                <!-- Recent Activity -->
                <div class="card">
                    <div class="card-header">
                        <h2>Recent Activity</h2>
                    </div>
                    <div class="timeline">
                        <div class="timeline-item">
                            <div class="timeline-icon">
                                <i class="fas fa-check"></i>
                            </div>
                            <div class="timeline-content">
                                <div class="timeline-title">Render Complete: Shot_042</div>
                                <div class="timeline-time">5 minutes ago</div>
                            </div>
                        </div>
                        <div class="timeline-item">
                            <div class="timeline-icon">
                                <i class="fas fa-eye"></i>
                            </div>
                            <div class="timeline-content">
                                <div class="timeline-title">New Review Request</div>
                                <div class="timeline-time">15 minutes ago</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tickets Card -->
                <div class="card">
                    <div class="card-header">
                        <h2>Tickets</h2>
                        <div class="header-actions">
                            <button class="create-ticket-btn" onclick="openTicketModal()">
                                <i class="fas fa-plus"></i> New Ticket
                            </button>
                        </div>
                    </div>
                    <div class="tickets-list">
                        <!-- Tickets will be loaded here dynamically -->
                        <div class="loading-message">Loading tickets...</div>
                    </div>
                </div>

                <!-- Add the ticket modal -->
                <div id="ticketModal" class="modal">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h2>Create New Ticket</h2>
                            <button class="close-btn" onclick="closeTicketModal()">&times;</button>
                        </div>
                        <form id="ticketForm" onsubmit="submitTicket(event)">
                            <div class="form-group">
                                <label for="title">Title</label>
                                <input type="text" id="title" name="title" required>
                            </div>
                            <div class="form-group">
                                <label for="description">Description</label>
                                <textarea id="description" name="description" required></textarea>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="priority">Priority</label>
                                    <select id="priority" name="priority" required>
                                        <option value="low">Low</option>
                                        <option value="medium">Medium</option>
                                        <option value="high">High</option>
                                        <option value="critical">Critical</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="type">Type</label>
                                    <select id="type" name="type" required>
                                        <option value="bug">Bug</option>
                                        <option value="feature">Feature</option>
                                        <option value="task">Task</option>
                                        <option value="technical_debt">Technical Debt</option>
                                    </select>
                                </div>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="submit-btn">Create Ticket</button>
                                <button type="button" class="cancel-btn" onclick="closeTicketModal()">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Old Tickets Card -->
                <div class="card">
                    <div class="card-header">
                        <h2>Old Tickets</h2>
                        <div class="status">
                            <i class="fas fa-history"></i>
                            Archive
                        </div>
                    </div>
                    <div class="tickets-list old-tickets-list">
                        <!-- Old tickets will be loaded here -->
                        <div class="loading-message">Loading archived tickets...</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Theme Toggle
            function toggleTheme() {
                const body = document.body;
                const themeToggle = document.querySelector('.theme-toggle i');
                
                body.dataset.theme = body.dataset.theme === 'dark' ? 'light' : 'dark';
                themeToggle.className = body.dataset.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
                
                updateCharts();
            }

            // Farm Usage Chart
            const farmCtx = document.getElementById('farmUsageChart').getContext('2d');
            const farmChart = new Chart(farmCtx, {
                type: 'line',
                data: {
                    labels: ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'],
                    datasets: [{
                        label: 'Farm Usage',
                        data: [65, 59, 80, 81, 56, 55, 70, 85],
                        fill: true,
                        borderColor: '#000000',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });

            // Resource Usage Chart
            const resourceCtx = document.getElementById('resourceChart').getContext('2d');
            const resourceChart = new Chart(resourceCtx, {
                type: 'bar',
                data: {
                    labels: ['CPU', 'Memory', 'GPU', 'Storage'],
                    datasets: [{
                        label: 'Usage %',
                        data: [85, 65, 90, 45],
                        backgroundColor: '#000000'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });

            // Update charts when theme changes
            function updateCharts() {
                const isDark = document.body.dataset.theme === 'dark';
                const color = isDark ? '#ffffff' : '#000000';
                
                farmChart.data.datasets[0].borderColor = color;
                resourceChart.data.datasets[0].backgroundColor = color;
                
                farmChart.update();
                resourceChart.update();
            }

            // Add this to your existing script section
            function openTicketModal() {
                document.getElementById('ticketModal').style.display = 'block';
            }

            function closeTicketModal() {
                document.getElementById('ticketModal').style.display = 'none';
            }

            async function submitTicket(event) {
                event.preventDefault();
                
                const formData = new FormData(event.target);
                const ticketData = {
                    title: formData.get('title'),
                    description: formData.get('description'),
                    priority: formData.get('priority'),
                    type: formData.get('type'),
                    project_id: 'project123' // You might want to make this dynamic
                };

                try {
                    const response = await fetch('/api/tickets', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(ticketData)
                    });

                    if (response.ok) {
                        closeTicketModal();
                        await loadTickets(); // Refresh the tickets list
                    } else {
                        throw new Error('Failed to create ticket');
                    }
                } catch (error) {
                    console.error('Error creating ticket:', error);
                    // Show error message to user
                }
            }

            async function loadTickets() {
                const ticketsList = document.querySelector('.tickets-list');
                
                try {
                    console.log('Fetching tickets...');
                    const response = await fetch('/api/tickets');
                    console.log('Response status:', response.status);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const tickets = await response.json();
                    console.log('Received tickets:', tickets);
                    
                    if (!Array.isArray(tickets)) {
                        throw new Error('Invalid response format');
                    }
                    
                    if (tickets.length === 0) {
                        ticketsList.innerHTML = `
                            <div class="empty-state">
                                No tickets found. Create a new ticket to get started.
                            </div>
                        `;
                        return;
                    }
                    
                    ticketsList.innerHTML = tickets.map(ticket => `
                        <div class="ticket-item">
                            <div class="ticket-info">
                                <div class="ticket-title">${ticket.title}</div>
                                <div class="ticket-meta">
                                    #${ticket.id} • Created by ${ticket.created_by}
                                </div>
                            </div>
                            <div class="ticket-status status-${ticket.status.toLowerCase()}">
                                ${ticket.status}
                            </div>
                        </div>
                    `).join('');
                    
                } catch (error) {
                    console.error('Error loading tickets:', error);
                    ticketsList.innerHTML = `
                        <div class="error-state">
                            <p>Failed to load tickets. Please try again later.</p>
                            <p class="error-details">${error.message}</p>
                        </div>
                    `;
                }
            }

            // Add this to verify the API is working
            async function checkApiHealth() {
                try {
                    const response = await fetch('/api/health');
                    const data = await response.json();
                    console.log('API health check:', data);
                    return data.status === 'healthy';
                } catch (error) {
                    console.error('API health check failed:', error);
                    return false;
                }
            }

            // Initialize when the page loads
            document.addEventListener('DOMContentLoaded', async () => {
                console.log('Checking API health...');
                const isHealthy = await checkApiHealth();
                
                if (isHealthy) {
                    console.log('API is healthy, loading tickets...');
                    await loadTickets();
                } else {
                    console.error('API health check failed');
                    const ticketsList = document.querySelector('.tickets-list');
                    ticketsList.innerHTML = `
                        <div class="error-state">
                            <p>Unable to connect to the ticket system.</p>
                            <p>Please try again later.</p>
                        </div>
                    `;
                }
            });

            // Close modal when clicking outside
            window.onclick = function(event) {
                const modal = document.getElementById('ticketModal');
                if (event.target === modal) {
                    closeTicketModal();
                }
            }

            async function loadOldTickets() {
                const oldTicketsList = document.querySelector('.old-tickets-list');
                
                try {
                    const response = await fetch('/api/old-tickets');
                    const tickets = await response.json();
                    
                    if (tickets.length === 0) {
                        oldTicketsList.innerHTML = `
                            <div class="empty-state">
                                <i class="fas fa-ticket-alt empty-icon"></i>
                                <p>No archived tickets found</p>
                            </div>
                        `;
                        return;
                    }
                    
                    oldTicketsList.innerHTML = tickets.map(ticket => {
                        // Extract ticket info using regex
                        const ticketInfo = parseTicketContent(ticket.content);
                        
                        return `
                            <div class="ticket-card">
                                <div class="ticket-header" onclick="toggleTicket(this)">
                                    <div class="ticket-meta">
                                        <span class="ticket-id">#${ticketInfo.id || 'Unknown'}</span>
                                        <span class="ticket-date">${new Date(ticket.last_modified).toLocaleDateString()}</span>
                                    </div>
                                    <div class="ticket-title">${ticketInfo.title || ticket.id}</div>
                                    <div class="ticket-tags">
                                        ${ticketInfo.tags.map(tag => `
                                            <span class="tag">${tag}</span>
                                        `).join('')}
                                    </div>
                                    <i class="fas fa-chevron-down expand-icon"></i>
                                </div>
                                <div class="ticket-content">
                                    <div class="ticket-details">
                                        <div class="detail-item">
                                            <i class="fas fa-user"></i>
                                            <span>Created by: ${ticketInfo.author || 'Unknown'}</span>
                                        </div>
                                        <div class="detail-item">
                                            <i class="fas fa-clock"></i>
                                            <span>Created: ${ticketInfo.created || 'Unknown'}</span>
                                        </div>
                                        ${ticketInfo.status ? `
                                            <div class="detail-item">
                                                <i class="fas fa-info-circle"></i>
                                                <span>Status: ${ticketInfo.status}</span>
                                            </div>
                                        ` : ''}
                                    </div>
                                    <div class="ticket-description">
                                        ${ticket.content}
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('');
                    
                } catch (error) {
                    console.error('Error:', error);
                    oldTicketsList.innerHTML = `
                        <div class="error-state">
                            <i class="fas fa-exclamation-circle"></i>
                            <p>Unable to load tickets</p>
                            <button onclick="loadOldTickets()">Try Again</button>
                        </div>
                    `;
                }
            }

            function parseTicketContent(content) {
                // Extract meaningful data from the markdown content
                const titleMatch = content.match(/^#\s*(.+)$/m);
                const authorMatch = content.match(/Created by:\s*(.+)$/m);
                const dateMatch = content.match(/Created on:\s*(.+)$/m);
                const statusMatch = content.match(/Status:\s*(.+)$/m);
                const tagsMatch = content.match(/Tags:\s*(.+)$/m);
                
                return {
                    title: titleMatch ? titleMatch[1] : null,
                    author: authorMatch ? authorMatch[1] : null,
                    created: dateMatch ? dateMatch[1] : null,
                    status: statusMatch ? statusMatch[1] : null,
                    tags: tagsMatch ? tagsMatch[1].split(',').map(t => t.trim()) : []
                };
            }

            function toggleTicket(header) {
                const card = header.closest('.ticket-card');
                card.classList.toggle('expanded');
            }
        </script>
    </body>
    </html>
    """

# Discord OAuth endpoints
@app.get("/auth/login")
async def discord_login():
    """Discord OAuth2 login endpoint"""
    oauth_url = (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id=1303089786495565875"  # Your client ID
        f"&permissions=8"  # Administrator permissions
        "&response_type=code"
        f"&redirect_uri={urllib.parse.quote('http://127.0.0.1:8000/auth/callback')}"
        "&scope=" + urllib.parse.quote(
            "bot "
            "applications.commands "
            "identify "
            "guilds "
            "guilds.members.read"
        )
    )
    
    logger.info(f"Redirecting to Discord OAuth URL: {oauth_url}")
    return RedirectResponse(url=oauth_url)

@app.get("/auth/callback")
async def discord_callback(code: str):
    """Discord OAuth2 callback endpoint"""
    try:
        # Exchange code for token
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI,
            'scope': 'identify guilds bot applications.commands'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://discord.com/api/oauth2/token', data=data) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to get access token")
                token_data = await response.json()
                
        # Get user info
        headers = {
            'Authorization': f"Bearer {token_data['access_token']}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discord.com/api/users/@me', headers=headers) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to get user info")
                user_data = await response.json()
        
        # Store user session info
        return {
            "user": user_data,
            "access_token": token_data['access_token']
        }
        
    except Exception as e:
        logger.error(f"Error in Discord callback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/debug/oauth")
async def debug_oauth():
    """Debug endpoint to verify OAuth configuration"""
    return {
        "client_id": DISCORD_CLIENT_ID[:5] + "..." if DISCORD_CLIENT_ID else None,
        "client_secret": "..." if DISCORD_CLIENT_SECRET else None,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "encoded_redirect": quote(DISCORD_REDIRECT_URI),
        "full_auth_url": f"https://discord.com/api/oauth2/authorize?{urlencode({
            'client_id': DISCORD_CLIENT_ID,
            'redirect_uri': DISCORD_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'identify guilds'
        })}"
    }

@app.get("/auth/bot-invite")
async def get_bot_invite():
    """Generate Discord bot invite URL"""
    permissions = 8  # Administrator permissions, adjust as needed
    url = f"https://discord.com/api/oauth2/authorize" \
          f"?client_id={DISCORD_CLIENT_ID}" \
          f"&permissions={permissions}" \
          f"&scope=bot%20applications.commands"
    return {"invite_url": url}

# Add new models
class RenderJob(BaseModel):
    id: str
    project_name: str
    shot_name: str
    status: str
    priority: int
    submitted_by: str
    start_time: Optional[datetime]
    estimated_completion: Optional[datetime]
    frame_range: str
    completion_percentage: float

class ProjectMilestone(BaseModel):
    id: str
    project_name: str
    title: str
    due_date: datetime
    status: str
    assignee: str
    description: str

# Add new models after your existing models
class Asset(BaseModel):
    id: str
    name: str
    type: str  # e.g., "model", "texture", "rig"
    status: str
    version: str
    created_by: str
    created_at: datetime
    modified_at: datetime
    file_path: str
    tags: List[str]
    dependencies: List[str]

class Review(BaseModel):
    id: str
    asset_id: str
    reviewer: str
    status: str  # "approved", "rejected", "pending"
    comments: str
    timestamp: datetime
    version_reviewed: str

class TimeLog(BaseModel):
    id: str
    user_id: str
    project_id: str
    task_id: str
    start_time: datetime
    end_time: Optional[datetime]
    description: str
    tags: List[str]

# Add these new endpoints before the main() check
@app.get("/api/assets")
async def get_assets(
    asset_type: Optional[str] = None,
    status: Optional[str] = None
) -> List[Asset]:
    """Get all assets with optional filtering"""
    # Implementation would query your database
    return []

@app.post("/api/assets/{asset_id}/review")
async def create_review(asset_id: str, review: Review):
    """Create a new review for an asset"""
    # Implementation would store the review
    return {"message": "Review created", "review_id": review.id}

@app.get("/api/statistics/productivity")
async def get_productivity_stats(
    start_date: datetime,
    end_date: datetime,
    project_id: Optional[str] = None
):
    """Get productivity statistics for specified time period"""
    return {
        "total_hours_logged": 160,
        "assets_completed": 25,
        "reviews_performed": 42,
        "average_review_time": "2.5 hours",
        "busiest_day": "Wednesday",
        "peak_hours": ["10:00", "14:00"],
        "department_breakdown": {
            "modeling": 45,
            "texturing": 30,
            "rigging": 25,
            "animation": 60
        }
    }

@app.get("/api/pipeline/dependencies")
async def get_pipeline_dependencies(shot_id: str):
    """Get all dependencies for a specific shot"""
    return {
        "shot_id": shot_id,
        "assets": [
            {"id": "asset1", "name": "character_rig", "status": "approved"},
            {"id": "asset2", "name": "environment", "status": "in_progress"}
        ],
        "upstream_tasks": [
            {"id": "task1", "name": "modeling", "status": "completed"},
            {"id": "task2", "name": "rigging", "status": "in_progress"}
        ],
        "downstream_tasks": [
            {"id": "task3", "name": "animation", "status": "pending"},
            {"id": "task4", "name": "lighting", "status": "pending"}
        ]
    }

@app.post("/api/pipeline/automated-tasks")
async def trigger_automated_task(
    task_type: str,
    target_id: str,
    parameters: dict
):
    """Trigger automated pipeline tasks"""
    supported_tasks = {
        "generate_thumbnails": "Creates thumbnails for review",
        "update_dependencies": "Updates all dependent files",
        "validate_scene": "Checks scene file for common issues",
        "backup_files": "Creates backup of specified files",
        "sync_to_farm": "Syncs files to render farm"
    }
    
    if task_type not in supported_tasks:
        raise HTTPException(status_code=400, detail="Unsupported task type")
    
    # Implementation would handle the automated task
    return {
        "task_id": "task_123",
        "status": "initiated",
        "estimated_completion": datetime.now() + timedelta(minutes=5)
    }

# Add new endpoints
@app.get("/api/render-queue")
async def get_render_queue() -> List[RenderJob]:
    """Get current render farm queue"""
    # Mock data - replace with actual database queries
    return [
        RenderJob(
            id="job123",
            project_name="Project Alpha",
            shot_name="SHOT_042",
            status="rendering",
            priority=1,
            submitted_by="user123",
            start_time=datetime.now() - timedelta(hours=2),
            estimated_completion=datetime.now() + timedelta(hours=1),
            frame_range="1001-1125",
            completion_percentage=65.5
        )
    ]

@app.post("/api/render-jobs")
async def submit_render_job(job: RenderJob):
    """Submit a new render job"""
    # Add implementation
    return {"message": "Job submitted successfully", "job_id": job.id}

@app.get("/api/projects/{project_id}/milestones")
async def get_project_milestones(project_id: str) -> List[ProjectMilestone]:
    """Get milestones for a specific project"""
    # Mock data - replace with actual database queries
    return [
        ProjectMilestone(
            id="milestone123",
            project_name="Project Alpha",
            title="Final Delivery",
            due_date=datetime.now() + timedelta(days=30),
            status="in_progress",
            assignee="user123",
            description="Deliver final composited shots"
        )
    ]

@app.get("/api/system/health")
async def get_system_health():
    """Get system health metrics"""
    return {
        "render_farm": {
            "status": "healthy",
            "active_nodes": 42,
            "total_nodes": 50,
            "cpu_usage": 87.5,
            "memory_usage": 75.2,
            "gpu_usage": 92.1
        },
        "storage": {
            "total_space": 500000,  # GB
            "used_space": 350000,   # GB
            "hot_storage_status": "healthy",
            "backup_status": "in_progress"
        },
        "services": {
            "deadline": "running",
            "nuke": "running",
            "houdini": "running",
            "maya": "warning"  # Example of a service with issues
        }
    }

@app.post("/api/notifications/discord")
async def send_discord_notification(
    channel_id: str,
    message: str,
    priority: str = "normal"
):
    """Send notification to Discord channel"""
    # Implement Discord webhook/bot message
    return {"message": "Notification sent"}

# Add these new models
class IssueComment(BaseModel):
    id: str
    content: str
    author: str
    created_at: datetime
    updated_at: Optional[datetime]
    attachments: List[str] = []

class Issue(BaseModel):
    id: str
    title: str
    description: str
    status: str  # "open", "in_progress", "resolved", "closed"
    priority: str  # "low", "medium", "high", "critical"
    type: str  # "bug", "feature", "task", "technical_debt"
    created_by: str
    assigned_to: Optional[str]
    project_id: str
    asset_id: Optional[str]
    shot_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]
    tags: List[str] = []
    comments: List[IssueComment] = []
    linked_issues: List[str] = []  # List of related issue IDs
    time_estimate: Optional[float]  # Hours
    time_spent: Optional[float]  # Hours
    environment: Optional[str]  # e.g., "maya_2024", "nuke_14.0"
    reproducibility_steps: Optional[str]
    attachments: List[str] = []  # List of attachment URLs/paths

# Add these new endpoints
@app.post("/api/issues")
async def create_issue(issue: Issue):
    """Create a new issue"""
    # Implementation would store the issue in database
    return {"message": "Issue created successfully", "issue_id": issue.id}

@app.get("/api/issues")
async def get_issues():
    """Get all issues"""
    # Implementation would query the database
    return []

# Add these new enums for ticket properties
class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    TECHNICAL_DEBT = "technical_debt"

# Add new ticket creation model
class TicketCreate(BaseModel):
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority
    type: TicketType
    assigned_to: Optional[str] = None
    project_id: str
    asset_id: Optional[str] = None
    shot_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: List[str] = []
    environment: Optional[str] = None
    reproducibility_steps: Optional[str] = None
    time_estimate: Optional[float] = None

# Add ticket response model
class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    type: TicketType
    created_by: str
    assigned_to: Optional[str]
    project_id: str
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]
    tags: List[str]
    environment: Optional[str]
    time_estimate: Optional[float]
    time_spent: Optional[float] = 0.0

# Add new endpoints
@app.post("/api/tickets", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate, current_user: str = "user123"):  # You would get current_user from auth
    """Create a new ticket/issue"""
    
    # Generate ticket ID (in production, this would come from your database)
    ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d')}-{hash(datetime.now())}"[:16]
    
    # Create response with additional fields
    response = TicketResponse(
        id=ticket_id,
        **ticket.dict(),
        created_by=current_user,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        time_spent=0.0
    )
    
    # Here you would typically:
    # 1. Save to database
    # 2. Send notifications
    # 3. Create audit log
    # 4. Handle any pipeline automation
    
    return response

@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str):
    """Get a specific ticket by ID"""
    # In production, query your database
    # For now, return mock data
    return TicketResponse(
        id=ticket_id,
        title="Sample Ticket",
        description="This is a sample ticket",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        type=TicketType.TASK,
        created_by="user123",
        assigned_to=None,
        project_id="project123",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["sample"],
        environment="maya_2024"
    )

@app.get("/api/tickets", response_model=List[TicketResponse])
async def list_tickets(
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    assigned_to: Optional[str] = None,
    project_id: Optional[str] = None
):
    """Get all tickets with optional filtering"""
    # In production, query your database with filters
    # For now, return mock data
    return [
        TicketResponse(
            id="TICKET-123",
            title="Sample Ticket",
            description="This is a sample ticket",
            status=TicketStatus.OPEN,
            priority=TicketPriority.MEDIUM,
            type=TicketType.TASK,
            created_by="user123",
            assigned_to=None,
            project_id="project123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["sample"],
            environment="maya_2024"
        )
    ]

# Add these new models for ticket comments and attachments
class TicketComment(BaseModel):
    content: str
    author: str
    created_at: datetime = Field(default_factory=datetime.now)
    attachments: List[str] = []

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None

# Add these new endpoints after your existing ticket endpoints
@app.put("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    current_user: str = "user123"  # In production, get from auth
):
    """Update an existing ticket"""
    # In production, validate ticket exists and user has permission
    
    # Mock response
    return TicketResponse(
        id=ticket_id,
        title=update.title or "Original Title",
        description=update.description or "Original Description",
        status=update.status or TicketStatus.OPEN,
        priority=update.priority or TicketPriority.MEDIUM,
        type=TicketType.TASK,
        created_by="original_user",
        assigned_to=update.assigned_to,
        project_id="project123",
        created_at=datetime.now() - timedelta(days=1),
        updated_at=datetime.now(),
        tags=update.tags or [],
        environment="maya_2024"
    )

@app.post("/api/tickets/{ticket_id}/comments")
async def add_ticket_comment(
    ticket_id: str,
    comment: TicketComment,
    current_user: str = "user123"  # In production, get from auth
):
    """Add a comment to a ticket"""
    return {
        "message": "Comment added successfully",
        "ticket_id": ticket_id,
        "comment_id": f"comment_{hash(datetime.now())}"
    }

@app.get("/api/tickets/{ticket_id}/history")
async def get_ticket_history(ticket_id: str):
    """Get the complete history of a ticket"""
    return {
        "ticket_id": ticket_id,
        "history": [
            {
                "timestamp": datetime.now() - timedelta(days=1),
                "type": "created",
                "user": "user123",
                "details": "Ticket created"
            },
            {
                "timestamp": datetime.now() - timedelta(hours=12),
                "type": "status_changed",
                "user": "user456",
                "details": "Status changed from 'open' to 'in_progress'"
            },
            {
                "timestamp": datetime.now() - timedelta(hours=2),
                "type": "comment_added",
                "user": "user789",
                "details": "Added comment: 'Working on this now'"
            }
        ]
    }

@app.post("/api/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    assignee: str,
    current_user: str = "user123"  # In production, get from auth
):
    """Assign a ticket to a user"""
    return {
        "message": "Ticket assigned successfully",
        "ticket_id": ticket_id,
        "assignee": assignee
    }

@app.get("/api/tickets/statistics")
async def get_ticket_statistics(
    project_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get statistics about tickets"""
    return {
        "total_tickets": 150,
        "status_breakdown": {
            "open": 45,
            "in_progress": 38,
            "resolved": 52,
            "closed": 15
        },
        "priority_breakdown": {
            "low": 30,
            "medium": 75,
            "high": 35,
            "critical": 10
        },
        "average_resolution_time": "3.5 days",
        "most_active_users": [
            {"user": "user123", "tickets_resolved": 25},
            {"user": "user456", "tickets_resolved": 18}
        ]
    }

# Define response models
class TicketBase(BaseModel):
    title: str
    description: str
    status: str = "open"
    priority: str
    type: str
    project_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Sample Ticket",
                "description": "This is a sample ticket",
                "priority": "medium",
                "type": "task",
                "project_id": "project123"
            }
        }

@app.get("/api/tickets", response_model=List[TicketResponse])
async def get_tickets():
    """Get all tickets"""
    try:
        logger.debug("Fetching tickets")
        # Mock data for testing
        tickets = [
            {
                "id": "TICKET-001",
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "status": "open",
                "priority": "medium",
                "type": "task",
                "created_by": "user123",
                "created_at": str(datetime.now()),
                "updated_at": str(datetime.now()),
                "project_id": "project123"
            }
        ]
        logger.debug(f"Retrieved tickets: {tickets}")
        return tickets
    except Exception as e:
        logger.error(f"Error fetching tickets: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tickets: {str(e)}"
        )

@app.post("/api/tickets", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate):
    """Create a new ticket"""
    try:
        # Mock response for testing
        return {
            "id": f"TICKET-{hash(datetime.now())}",
            "title": ticket.title,
            "description": ticket.description,
            "status": "open",
            "priority": ticket.priority,
            "type": ticket.type,
            "created_by": "user123",  # This would come from auth
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "project_id": ticket.project_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add a debug endpoint to help troubleshoot
@app.get("/api/debug/tickets")
async def debug_tickets():
    """Debug endpoint to check ticket system"""
    return {
        "status": "running",
        "timestamp": str(datetime.now()),
        "models": {
            "TicketBase": str(TicketBase.schema()),
            "TicketCreate": str(TicketCreate.schema()),
            "TicketResponse": str(TicketResponse.schema())
        }
    }

# Add a test endpoint to verify the API is working
@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API functionality"""
    return {"status": "ok", "timestamp": str(datetime.now())}

# Add this after your existing routes
@app.get("/api/old-tickets")
async def get_old_tickets():
    """Get all old tickets from markdown files"""
    tickets_dir = Path("/Users/martintomek/vfx-discord-app/tickets")
    tickets = []
    
    try:
        for md_file in tickets_dir.glob("*.md"):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Convert markdown to HTML
                html_content = markdown.markdown(content)
                
                tickets.append({
                    "id": md_file.stem,  # filename without extension
                    "content": html_content,
                    "file_path": str(md_file),
                    "last_modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
                })
        
        return sorted(tickets, key=lambda x: x["last_modified"], reverse=True)
    except Exception as e:
        logger.error(f"Error reading ticket files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading ticket files: {str(e)}"
        )

# Configuration
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = 1070668995105140858  # Your server ID

# Initialize bot only if token is available
bot = None
if DISCORD_BOT_TOKEN:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    intents.reactions = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        """Called when the bot is ready and connected"""
        try:
            guild = bot.get_guild(GUILD_ID)
            if guild:
                print(f'Successfully connected to: {guild.name}')
                # Create or get ticket category
                category = discord.utils.get(guild.categories, name='Tickets')
                if not category:
                    category = await guild.create_category('Tickets')
                    print(f'Created Tickets category')
            else:
                print(f'Could not find guild with ID: {GUILD_ID}')
                
            print(f'Bot is ready! Logged in as {bot.user.name}')
            print(f'Bot ID: {bot.user.id}')
            
        except Exception as e:
            print(f'Error in on_ready: {e}')

    # Only register commands if bot is initialized
    @bot.command(name='help_ticket')
    async def help_ticket(ctx):
        """Show ticket system help"""
        embed = discord.Embed(
            title="Ticket System Help",
            description="Here's how to use the ticket system:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Create a ticket",
            value="!ticket <your message>",
            inline=False
        )
        embed.add_field(
            name="Ticket Management",
            value="Use reactions in the ticket channel:\n✅ - Complete\n🔄 - In Progress\n❌ - Close",
            inline=False
        )
        await ctx.send(embed=embed)

    @bot.command(name='ping')
    async def ping(ctx):
        """Check if bot is responsive"""
        await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

    @bot.command(name='app')
    async def open_app(ctx):
        """Provides a link to the web interface"""
        embed = discord.Embed(
            title="VFX Ticket System",
            description="Click below to access the ticket system:",
            color=discord.Color.blue()
        )
        
        # Add buttons using discord components
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Open Ticket System",
            url="http://127.0.0.1:8000",
            style=discord.ButtonStyle.link
        ))
        
        await ctx.send(embed=embed, view=view)

    @bot.command(name='dashboard')
    async def show_dashboard(ctx):
        """Shows ticket statistics directly in Discord"""
        try:
            embed = discord.Embed(
                title="Ticket System Dashboard",
                color=discord.Color.blue()
            )
            
            # Add ticket statistics
            embed.add_field(
                name="Quick Links",
                value="🔗 [Open Dashboard](http://127.0.0.1:8000)\n📊 [View Statistics](http://127.0.0.1:8000/api/tickets/statistics)",
                inline=False
            )
            
            embed.add_field(
                name="Commands",
                value="""
                `!ticket` - Create a new ticket
                `!help_ticket` - Show help
                `!app` - Get app link
                """,
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error showing dashboard: {str(e)}")
else:
    print("Discord bot disabled - DISCORD_BOT_TOKEN not set")

# FastAPI startup event
@app.on_event("startup")
async def startup_event():
    """Start the Discord bot when the FastAPI app starts"""
    if bot and DISCORD_BOT_TOKEN:
        try:
            logger.info("Initializing Discord bot...")
            # Create background task for bot
            bot_task = asyncio.create_task(bot.start(DISCORD_BOT_TOKEN))
            
            # Add error handling for the background task
            def handle_bot_error(task):
                try:
                    task.result()
                except Exception as e:
                    logger.error(f"Discord bot crashed: {str(e)}", exc_info=True)
                    
            bot_task.add_done_callback(handle_bot_error)
            logger.info("Discord bot startup initiated successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {str(e)}", exc_info=True)
            raise RuntimeError(f"Bot initialization failed: {str(e)}")
    else:
        logger.warning("Discord bot disabled - DISCORD_BOT_TOKEN not set or bot not initialized")

# Add status check endpoint
@app.get("/api/bot/status")
async def get_bot_status():
    """Check Discord bot status"""
    if not bot:
        return {"status": "disabled", "reason": "Bot not initialized"}
        
    try:
        return {
            "status": "online" if bot.is_ready() else "connecting",
            "latency": round(bot.latency * 1000, 2),
            "guilds": len(bot.guilds),
            "user": str(bot.user) if bot.user else None
        }
    except Exception as e:
        logger.error(f"Error checking bot status: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}
        print("Discord bot disabled - DISCORD_BOT_TOKEN not set")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)