"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronDown, Search, Globe, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { sreClient } from "@/lib/api-client";

interface Project {
    id: string;
    name: string;
}

interface ProjectSelectorProps {
    currentProjectId: string;
    onProjectChange: (projectId: string) => void;
    className?: string;
}

export function ProjectSelector({
    currentProjectId,
    onProjectChange,
    className,
}: ProjectSelectorProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        async function fetchProjects() {
            setLoading(true);
            try {
                const data = await sreClient.listProjects();
                if (data && data.projects) {
                    setProjects(data.projects);
                }
            } catch (error) {
                console.error("Failed to fetch projects:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchProjects();
    }, []);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const filteredProjects = projects.filter(
        (p) =>
            p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
            p.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const selectedProject = projects.find((p) => p.id === currentProjectId);

    return (
        <div className={cn("relative z-50", className)} ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-300",
                    "bg-card/40 backdrop-blur-md border-border/50 hover:border-primary/50",
                    "text-xs font-medium text-foreground/80 shadow-lg shadow-black/20"
                )}
            >
                <Globe className="h-3.5 w-3.5 text-primary" />
                <span className="max-w-[120px] truncate">
                    {selectedProject ? selectedProject.name : currentProjectId}
                </span>
                <ChevronDown
                    className={cn(
                        "h-3.5 w-3.5 transition-transform duration-300",
                        isOpen && "rotate-180"
                    )}
                />
            </button>

            {isOpen && (
                <div
                    className={cn(
                        "absolute right-0 mt-2 w-72 rounded-xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300",
                        "bg-card/90 backdrop-blur-xl border border-border/60 shadow-2xl ring-1 ring-black/5"
                    )}
                >
                    <div className="p-3 border-b border-white/5">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                            <input
                                autoFocus
                                type="text"
                                placeholder="Search or enter project ID..."
                                className="w-full bg-background/50 border border-border/40 rounded-lg pl-8 pr-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary/50"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && searchQuery) {
                                        onProjectChange(searchQuery);
                                        setIsOpen(false);
                                    }
                                }}
                            />
                        </div>
                    </div>

                    <div className="max-h-60 overflow-y-auto py-1 custom-scrollbar">
                        {loading ? (
                            <div className="px-4 py-8 text-center text-xs text-muted-foreground animate-pulse">
                                Fetching projects...
                            </div>
                        ) : filteredProjects.length > 0 ? (
                            filteredProjects.map((project) => (
                                <button
                                    key={project.id}
                                    onClick={() => {
                                        onProjectChange(project.id);
                                        setIsOpen(false);
                                    }}
                                    className={cn(
                                        "w-full text-left px-4 py-2 text-xs transition-colors hover:bg-primary/10 flex flex-col gap-0.5",
                                        project.id === currentProjectId && "bg-primary/5 border-l-2 border-primary"
                                    )}
                                >
                                    <span className="font-semibold text-foreground/90">
                                        {project.name}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                                        {project.id}
                                    </span>
                                </button>
                            ))
                        ) : searchQuery ? (
                            <button
                                onClick={() => {
                                    onProjectChange(searchQuery);
                                    setIsOpen(false);
                                }}
                                className="w-full text-left px-4 py-3 text-xs hover:bg-primary/10 flex items-center gap-3"
                            >
                                <div className="p-1.5 rounded-md bg-primary/20 text-primary">
                                    <Plus className="h-3.5 w-3.5" />
                                </div>
                                <div className="flex flex-col">
                                    <span className="font-medium text-foreground">Use custom ID</span>
                                    <span className="text-[10px] text-muted-foreground font-mono">{searchQuery}</span>
                                </div>
                            </button>
                        ) : (
                            <div className="px-4 py-8 text-center text-xs text-muted-foreground">
                                No projects found.
                            </div>
                        )}
                    </div>

                    <div className="p-2 bg-black/20 border-t border-white/5">
                        <p className="text-[9px] text-center text-muted-foreground/60 uppercase tracking-widest font-medium">
                            GCP Project Context
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
