'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import ProductForm from '../components/ProductForm';
import { adminAPI } from '@/services/api';

interface ProductFormData {
  id?: string;
  name: string;
  category_id: string;
  price: string;
  old_price: string;
  description: string;
  in_stock: boolean;
  quantity: number;
  images: Array<{
    id: string;
    url: string;
    thumbnail: string;
    alt_text: string;
    is_feature: boolean;
  }>;
}

const EditProductPage = () => {
  const params = useParams();
  const id = params.id as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [productData, setProductData] = useState<ProductFormData | null>(null);

  useEffect(() => {
    const fetchProduct = async () => {
      if (!id) {
        setError('Product ID is required');
        setLoading(false);
        return;
      }

      try {
        const data = await adminAPI.getProduct(id);
        // Преобразуем данные в формат, ожидаемый формой
        setProductData({
          id: data.id,
          name: data.name,
          category_id: data.category.id,
          price: Number(data.price).toFixed(2),
          old_price: data.old_price ? Number(data.old_price).toFixed(2) : '',
          description: data.description,
          in_stock: data.in_stock,
          quantity: data.quantity,
          images: data.images.map((img: any) => ({
            id: img.id,
            url: img.image,
            thumbnail: img.thumbnail,
            alt_text: img.alt_text,
            is_feature: img.is_feature
          }))
        });
      } catch (error) {
        console.error('Error fetching product:', error);
        setError(error instanceof Error ? error.message : 'Failed to fetch product');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchProduct();
    }
  }, [id]);

  if (loading) return <div className="loading">Загрузка...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!productData) return null;

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1>Редактирование товара</h1>
      </div>
      <ProductForm initialData={productData} isEdit={true} />
    </div>
  );
};

export default EditProductPage; 