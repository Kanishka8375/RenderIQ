import Header from './components/Header';
import Footer from './components/Footer';
import Home from './pages/Home';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg)]">
      <Header />
      <main className="flex-1 pt-20 pb-8">
        <Home />
      </main>
      <Footer />
    </div>
  );
}
