import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App'
import './index.css'

// Detect guest mode and user identity from URL query params (set by Flutter parent iframe)
const urlParams = new URLSearchParams(window.location.search)
const guestMode = urlParams.get('guest_mode') === 'true'
const userId = urlParams.get('user_id')

// Enable sending cookies (sre_session_id) on all requests
axios.defaults.withCredentials = true

if (guestMode) {
  axios.defaults.headers.common['X-Guest-Mode'] = 'true'
  axios.defaults.headers.common['Authorization'] = 'Bearer dev-mode-bypass-token'
}

if (userId) {
  axios.defaults.headers.common['X-User-ID'] = userId
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
