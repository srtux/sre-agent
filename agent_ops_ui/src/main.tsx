import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App'
import './index.css'

// Detect guest mode from URL query params (set by Flutter parent iframe)
const urlParams = new URLSearchParams(window.location.search)
if (urlParams.get('guest_mode') === 'true') {
  axios.defaults.headers.common['X-Guest-Mode'] = 'true'
  axios.defaults.headers.common['Authorization'] = 'Bearer dev-mode-bypass-token'
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
