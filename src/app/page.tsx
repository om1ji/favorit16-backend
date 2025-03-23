"use client";

import React, { useState, useEffect } from "react";
import HeroSection from "@/components/sections/HeroSection";
import Features from "@/components/sections/Features";
import Categories from "@/components/sections/Categories";
import PopularProducts from "@/components/sections/PopularProducts";
import LatestNews from "@/components/sections/LatestNews";
import Newsletter from "@/components/sections/Newsletter";
import TestModeAlert from "@/components/ui/TestModeAlert";
import { defaultConfig } from "@/lib/config/default-config";

export default function Home() {
  const [showAlert, setShowAlert] = useState(true);

  const handleCloseAlert = () => {
    setShowAlert(false);
  };

  return (
    <>
      <HeroSection />
      <Features />
      <Categories />
      <PopularProducts />
      {/* <LatestNews /> */}
      <Newsletter />

      {showAlert && (
        <TestModeAlert
          onClose={handleCloseAlert}
          phone={defaultConfig.contacts.phone}
          telegram={defaultConfig.social.telegram.url}
        />
      )}
    </>
  );
}
