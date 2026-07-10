import { useEffect, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { getEntreprise } from './api/client';
import Layout from './components/Layout';
import Catalog from './pages/Catalog';
import Home from './pages/Home';
import ProductDetail from './pages/ProductDetail';
import { BRAND_NAME } from './config/brand';
import type { Entreprise } from './types';

const defaultEntreprise: Entreprise = {
  raison_sociale: BRAND_NAME,
  slogan: 'Serving those who care for others',
  site_web: 'https://avalonpharmasenegal.com',
  adresse: '',
  telephone: '',
  email: 'avalonpharmasenegal@gmail.com',
  rc: '',
  ninea: '',
  pied_de_page: null,
};

export default function App() {
  const [entreprise, setEntreprise] = useState<Entreprise>(defaultEntreprise);

  useEffect(() => {
    getEntreprise()
      .then(setEntreprise)
      .catch(() => {});
  }, []);

  return (
    <Layout entreprise={entreprise}>
      <Routes>
        <Route path="/" element={<Home entreprise={entreprise} />} />
        <Route path="/catalogue" element={<Catalog />} />
        <Route path="/catalogue/:id" element={<ProductDetail />} />
      </Routes>
    </Layout>
  );
}
