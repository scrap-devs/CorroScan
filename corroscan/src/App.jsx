import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Extraction from './pages/Extraction'
import Home from './pages/Home'


function App() {

  return (
    <>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/extraction" element={<Extraction />} />
      </Routes>
    </BrowserRouter>
    </>
  )
}

export default App
