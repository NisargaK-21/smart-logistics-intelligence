"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  Alert,
  Coordinates,
  CoverageResponse,
  DashboardSummary,
  FieldReport,
  FieldReportCreate,
  HealthResponse,
  MockScenario,
  RiskSource,
  Route,
  VehiclePosition,
  VehicleType,
} from "./types";
import {
  createFieldReport,
  getActiveVehicles,
  getAlerts,
  getCoverage,
  getDashboardSummary,
  getFieldReports,
  getHealth,
  planRoutes,
} from "./api";
import { DEFAULT_CORRIDOR_BBOX, DEFAULT_CORRIDOR_ID } from "./constants";

interface AppContextType {
  // Mode & Health
  isMockMode: boolean;
  setIsMockMode: (val: boolean) => void;
  mockScenario: MockScenario;
  setMockScenario: (scenario: MockScenario) => void;
  health: HealthResponse | null;
  isHealthLoading: boolean;
  refreshHealth: () => Promise<void>;
  coverage: CoverageResponse | null;
  activeBbox: [number, number, number, number];
  summary: DashboardSummary | null;
  isSummaryLoading: boolean;
  refreshSummary: () => Promise<void>;

  // Corridor & UI Navigation
  selectedCorridor: string;
  setSelectedCorridor: (c: string) => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  isMobileSidebarOpen: boolean;
  setIsMobileSidebarOpen: (open: boolean) => void;

  // Route Planning
  origin: Coordinates | null;
  setOrigin: (coords: Coordinates | null) => void;
  destination: Coordinates | null;
  setDestination: (coords: Coordinates | null) => void;
  vehicleType: VehicleType;
  setVehicleType: (type: VehicleType) => void;
  departureTime: string;
  setDepartureTime: (time: string) => void;
  pickingMode: "origin" | "destination" | null;
  setPickingMode: (mode: "origin" | "destination" | null) => void;
  routes: Route[];
  setRoutes: (routes: Route[]) => void;
  recommendedRouteId: string;
  setRecommendedRouteId: (id: string) => void;
  selectedRouteId: string;
  setSelectedRouteId: (id: string) => void;
  activeRoute: Route | undefined;
  riskSource: RiskSource;
  isPlanningLoading: boolean;
  planCurrentRoutes: () => Promise<void>;
  error: unknown | null;
  setError: (err: unknown | null) => void;

  // Vehicles, Reports, Alerts
  vehicles: VehiclePosition[];
  isVehiclesLoading: boolean;
  refreshVehicles: () => Promise<void>;
  fieldReports: FieldReport[];
  isReportsLoading: boolean;
  refreshReports: () => Promise<void>;
  submitReport: (rep: FieldReportCreate) => Promise<FieldReport>;
  alerts: Alert[];
  refreshAlerts: () => Promise<void>;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  // Mode state
  const [isMockMode, setIsMockMode] = useState(false);
  const [mockScenario, setMockScenario] = useState<MockScenario>("success");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  // Corridor & UI
  const [selectedCorridor, setSelectedCorridor] = useState(DEFAULT_CORRIDOR_ID);
  const [searchQuery, setSearchQuery] = useState("");
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Route Planning state
  const [origin, setOrigin] = useState<Coordinates | null>({
    lat: 26.1445,
    lng: 91.7362,
  });
  const [destination, setDestination] = useState<Coordinates | null>({
    lat: 26.1801,
    lng: 91.7001,
  });
  const [vehicleType, setVehicleType] = useState<VehicleType>("truck");
  const [departureTime, setDepartureTime] = useState<string>("");
  const [pickingMode, setPickingMode] = useState<"origin" | "destination" | null>(null);

  // Results state
  const [routes, setRoutes] = useState<Route[]>([]);
  const [recommendedRouteId, setRecommendedRouteId] = useState<string>("");
  const [selectedRouteId, setSelectedRouteId] = useState<string>("");
  const [riskSource, setRiskSource] = useState<RiskSource>("baseline");
  const [isPlanningLoading, setIsPlanningLoading] = useState(false);
  const [error, setError] = useState<unknown | null>(null);

  // Vehicles, Reports, Alerts
  const [vehicles, setVehicles] = useState<VehiclePosition[]>([]);
  const [isVehiclesLoading, setIsVehiclesLoading] = useState(false);
  const [fieldReports, setFieldReports] = useState<FieldReport[]>([]);
  const [isReportsLoading, setIsReportsLoading] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  // Load health & summary
  const refreshHealth = useCallback(async () => {
    setIsHealthLoading(true);
    try {
      const res = await getHealth({ mock: isMockMode });
      setHealth(res);
    } catch {
      setHealth({
        status: "impaired",
        modules: { gis: "unavailable", risk: "unavailable", weather: "unavailable" },
      });
    } finally {
      setIsHealthLoading(false);
    }
  }, [isMockMode]);

  const refreshSummary = useCallback(async () => {
    setIsSummaryLoading(true);
    try {
      const res = await getDashboardSummary({ mock: isMockMode });
      setSummary(res);
    } catch {
      // Keep previous or default
    } finally {
      setIsSummaryLoading(false);
    }
  }, [isMockMode]);

  const refreshVehicles = useCallback(async () => {
    setIsVehiclesLoading(true);
    try {
      const res = await getActiveVehicles({ mock: isMockMode });
      setVehicles(res);
    } catch {
      // Ignore
    } finally {
      setIsVehiclesLoading(false);
    }
  }, [isMockMode]);

  const refreshReports = useCallback(async () => {
    setIsReportsLoading(true);
    try {
      const res = await getFieldReports(undefined, { mock: isMockMode });
      setFieldReports(res);
    } catch {
      // Ignore
    } finally {
      setIsReportsLoading(false);
    }
  }, [isMockMode]);

  const refreshAlerts = useCallback(async () => {
    try {
      const res = await getAlerts(undefined, { mock: isMockMode });
      setAlerts(res);
    } catch {
      // Ignore
    }
  }, [isMockMode]);

  const submitReport = useCallback(
    async (rep: FieldReportCreate): Promise<FieldReport> => {
      const created = await createFieldReport(rep, { mock: isMockMode });
      setFieldReports((prev) => [created, ...prev]);
      return created;
    },
    [isMockMode]
  );

  // Initial load
  useEffect(() => {
    let isSubscribed = true;

    async function init() {
      const [hRes, cRes, sRes, vRes, rRes, aRes] = await Promise.allSettled([
        getHealth({ mock: isMockMode }),
        getCoverage({ mock: isMockMode }),
        getDashboardSummary({ mock: isMockMode }),
        getActiveVehicles({ mock: isMockMode }),
        getFieldReports(undefined, { mock: isMockMode }),
        getAlerts(undefined, { mock: isMockMode }),
      ]);

      if (!isSubscribed) return;

      if (hRes.status === "fulfilled") {
        setHealth(hRes.value);
      } else {
        setHealth({
          status: "impaired",
          modules: { gis: "unavailable", risk: "unavailable", weather: "unavailable" },
        });
      }

      if (cRes.status === "fulfilled") setCoverage(cRes.value);
      if (sRes.status === "fulfilled") setSummary(sRes.value);
      if (vRes.status === "fulfilled") setVehicles(vRes.value);
      if (rRes.status === "fulfilled") setFieldReports(rRes.value);
      if (aRes.status === "fulfilled") setAlerts(aRes.value);
    }

    void init();

    return () => {
      isSubscribed = false;
    };
  }, [isMockMode]);

  // Execute Route Planning
  const planCurrentRoutes = async () => {
    if (!origin || !destination) return;

    setIsPlanningLoading(true);
    setError(null);

    try {
      const res = await planRoutes(
        {
          origin,
          destination,
          vehicle_type: vehicleType,
          departure_time: departureTime ? new Date(departureTime).toISOString() : undefined,
        },
        {
          mock: isMockMode,
          scenario: mockScenario,
        }
      );

      setRoutes(res.routes || []);
      setRecommendedRouteId(res.recommended_route_id);
      setSelectedRouteId(res.recommended_route_id);
      setRiskSource(res.risk_source);
      setPickingMode(null);
    } catch (err) {
      setError(err);
      setRoutes([]);
    } finally {
      setIsPlanningLoading(false);
    }
  };

  const activeRoute =
    routes.find((r) => r.route_id === selectedRouteId) ||
    routes.find((r) => r.route_id === recommendedRouteId) ||
    routes[0];

  const activeBbox = coverage?.bbox || DEFAULT_CORRIDOR_BBOX;

  return (
    <AppContext.Provider
      value={{
        isMockMode,
        setIsMockMode,
        mockScenario,
        setMockScenario,
        health,
        isHealthLoading,
        refreshHealth,
        coverage,
        activeBbox,
        summary,
        isSummaryLoading,
        refreshSummary,
        selectedCorridor,
        setSelectedCorridor,
        searchQuery,
        setSearchQuery,
        isMobileSidebarOpen,
        setIsMobileSidebarOpen,
        origin,
        setOrigin,
        destination,
        setDestination,
        vehicleType,
        setVehicleType,
        departureTime,
        setDepartureTime,
        pickingMode,
        setPickingMode,
        routes,
        setRoutes,
        recommendedRouteId,
        setRecommendedRouteId,
        selectedRouteId,
        setSelectedRouteId,
        activeRoute,
        riskSource,
        isPlanningLoading,
        planCurrentRoutes,
        error,
        setError,
        vehicles,
        isVehiclesLoading,
        refreshVehicles,
        fieldReports,
        isReportsLoading,
        refreshReports,
        submitReport,
        alerts,
        refreshAlerts,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp(): AppContextType {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
