using Agents
using Random
using LinearAlgebra
using DataStructures

# Agentes 
@agent struct Ghost(GridAgent{2})
    type::String
    has_key::Bool
    is_evil::Bool
    path::Vector{Tuple{Int,Int}}  # Camino planificado
    path_index::Int                # Índice actual en el camino
end

@agent struct Key(GridAgent{2})
    is_hidden::Bool     
    is_visible::Bool    
    is_collected::Bool  
end

function heuristic(a::NTuple{2,Int}, b::NTuple{2,Int})
    return abs(a[1] - b[1]) + abs(a[2] - b[2])  # Distancia Manhattan
end

function get_neighbors(pos::NTuple{2,Int}, size::NTuple{2,Int})
    neighbors = Tuple{Int,Int}[]
    directions = [(0,1), (1,0), (0,-1), (-1,0)]  # Arriba, Derecha, Abajo, Izquierda
    
    for (dx, dy) in directions
        new_pos = (pos[1] + dx, pos[2] + dy)
        if 1 <= new_pos[1] <= size[1] && 1 <= new_pos[2] <= size[2]
            push!(neighbors, new_pos)
        end
    end
    
    return neighbors
end

function a_star(start::NTuple{2,Int}, goal::NTuple{2,Int}, model)
    if start == goal
        return [goal]
    end
    
    size = Agents.spacesize(model)
    
    # Priority queue: (f_score, posición)
    open_set = PriorityQueue{NTuple{2,Int}, Float64}()
    open_set[start] = heuristic(start, goal)
    
    came_from = Dict{NTuple{2,Int}, NTuple{2,Int}}()
    g_score = Dict{NTuple{2,Int}, Float64}()
    g_score[start] = 0.0

    max_iterations = 1000  # Prevenir loops infinitos
    iterations = 0
    
    while !isempty(open_set) && iterations < max_iterations
        iterations += 1
        current = dequeue!(open_set)
        
        if current == goal
            # Reconstruir camino
            path = [current]
            while haskey(came_from, current)
                current = came_from[current]
                pushfirst!(path, current)
            end
            return path
        end
        
        for neighbor in get_neighbors(current, size)
            tentative_g = g_score[current] + 1.0
            
            if !haskey(g_score, neighbor) || tentative_g < g_score[neighbor]
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                open_set[neighbor] = f_score
            end
        end
    end
    
    # No se encontró camino, devolver camino directo simple
    @warn "A* no encontró camino, usando movimiento directo"
    return [start, goal]
end

function search_in_radius(center_pos::NTuple{2,Int}, radius::Real, model)
    for agent in allagents(model)
        if agent isa Key && agent.is_visible && !agent.is_collected
            distance = sqrt(sum((center_pos .- agent.pos).^2))
            if distance <= radius
                return (agent, distance)
            end
        end
    end
    return nothing
end

function find_closest_key(ghost_pos::NTuple{2,Int}, model)
    closest_key = nothing
    min_dist = Inf
    
    for agent in allagents(model)
        if agent isa Key && agent.is_visible && !agent.is_collected
            dist = sqrt(sum((ghost_pos .- agent.pos).^2))
            if dist < min_dist
                min_dist = dist
                closest_key = agent
            end
        end
    end
    
    return closest_key
end

# Comportamiento del fantasma (guía y ladrón) 
function agent_step!(agent, model)
    if agent isa Ghost
        # COMPORTAMIENTO MALO (Ladrón)
        if agent.is_evil

            # Si no tiene un camino válido o llegó al destino, buscar nueva llave
            need_new_path = isempty(agent.path) || agent.path_index > length(agent.path)

            # También necesitamos nuevo camino si llegamos a la posición actual del path
            if !need_new_path && agent.path_index <= length(agent.path)
                if agent.pos == agent.path[agent.path_index]
                    agent.path_index += 1
                    if agent.path_index > length(agent.path)
                        need_new_path = true
                    end
                end
            end

            if need_new_path
                max_search_radius = 8.0
                search_step = 2.0
                target_key = nothing
                
                # Buscar llave más cercana dentro del radio
                for radius in 1.0:search_step:max_search_radius
                    result = search_in_radius(agent.pos, radius, model)
                    if !isnothing(result)
                        target_key, _ = result
                        break
                    end
                end
                
                # Si no encontró llave cercana, buscar la más cercana globalmente
                if isnothing(target_key)
                    target_key = find_closest_key(agent.pos, model)
                end
                
                if !isnothing(target_key)
                    # Calcular nuevo camino usando A*
                    try
                        agent.path = a_star(agent.pos, target_key.pos, model)
                        agent.path_index = 2  # Índice 1 es la posición actual, empezamos en 2
                        
                        if !isempty(agent.path) && length(agent.path) > 1
                            @info "Fantasma malo calculó camino de $(length(agent.path)) pasos hacia $(target_key.pos)"
                        end
                    catch e
                        @warn "Error calculando camino A*: $e"
                        agent.path = Tuple{Int,Int}[]
                        agent.path_index = 1
                    end
                end
            end
            
            # Seguir el camino calculado
            if !isempty(agent.path) && agent.path_index <= length(agent.path)
                next_pos = agent.path[agent.path_index]
                
                # Verificar si puede moverse
                agents_there = agents_in_position(next_pos, model)
                can_move = true
                for occ in agents_there
                    if !(occ isa Key)
                        can_move = false
                    end
                end
                
                if can_move
                    move_agent!(agent, next_pos, model)
                    agent.path_index += 1
                    
                    # Verificar si llegó a una llave
                    for key_agent in agents_in_position(agent.pos, model)
                        if key_agent isa Key && key_agent.is_visible && !key_agent.is_collected
                            agent.has_key = true
                            key_agent.is_collected = true
                            key_agent.is_visible = false
                            @info "Fantasma se comió la llave en $(agent.pos)"
                            
                            # Limpiar camino para buscar siguiente llave
                            agent.path = Tuple{Int,Int}[]
                            agent.path_index = 1
                            break
                        end
                    end
                else
                    # Camino bloqueado, recalcular
                    agent.path = Tuple{Int,Int}[]
                    agent.path_index = 1
                end
            else
                # No hay camino, moverse aleatoriamente
                randomwalk!(agent, model)
            end
        
        # COMPORTAMIENTO BUENO (Guía)
        else
            # Si no tiene camino o llegó al destino, buscar nueva llave
            if isempty(agent.path) || agent.path_index > length(agent.path)
                closest_key = find_closest_key(agent.pos, model)
                
                if !isnothing(closest_key)
                    # Si ya está en la posición de la llave, quedarse quieto
                    if agent.pos == closest_key.pos
                        return
                    end
                    
                    # Calcular nuevo camino
                    try
                        agent.path = a_star(agent.pos, closest_key.pos, model)
                        agent.path_index = 1
                        
                        if !isempty(agent.path)
                            @info "Fantasma guía calculó camino de $(length(agent.path)) pasos hacia $(closest_key.pos)"
                        end
                    catch e
                        @warn "Error calculando camino A*: $e"
                        agent.path = Tuple{Int,Int}[]
                        agent.path_index = 1
                    end
                end
            end

            # Seguir el camino
            if !isempty(agent.path) && agent.path_index <= length(agent.path)
                next_pos = agent.path[agent.path_index]
                
                # Si llegó a la llave, quedarse ahí
                if next_pos == agent.path[end]
                    agents_there = agents_in_position(next_pos, model)
                    has_key_here = any(a -> a isa Key && a.is_visible && !a.is_collected, agents_there)
                    
                    if has_key_here && agent.pos == next_pos
                        return  # Quedarse en la llave
                    end
                end

                # Mover al siguiente paso
                agents_there = agents_in_position(next_pos, model)
                can_move = true
                for occ in agents_there
                    if !(occ isa Key)
                        can_move = false
                    end
                end

                if can_move
                    move_agent!(agent, next_pos, model)
                    agent.path_index += 1
                else
                    # Camino bloqueado, recalcular
                    agent.path = Tuple{Int,Int}[]
                    agent.path_index = 1
                end
            else 
                # No hay llave, moverse aleatoriamente
                randomwalk!(agent, model)
            end
        end
    end
end

# Inicializar modelo 
function initialize_model(; size=(10,10), key_positions=[])
    space = GridSpace(size; periodic=false, metric = :manhattan)
    model = StandardABM(Union{Ghost, Key}, space; agent_step! = agent_step!, scheduler = Schedulers.Randomly(), warn=false)

    # ID para el fantasma: 1
    # Crear fantasma con campos de pathfinding
    ghost = Ghost(1, (5, 5), "ghost", false, false, Tuple{Int,Int}[], 1)
    add_agent_own_pos!(ghost, model)

    # ID para las llaves: 2 en adelante
    # contador 'i' empieza en 1 así que + 1 para que el primer ID sea 2
    for (i, pos) in enumerate(key_positions)
        key_id = i + 1
        key = Key(key_id, pos, false, true, false)
        add_agent_own_pos!(key, model)
    end
    return model
end

function randomwalk!(a::Ghost, model)
    dirs = (-1:1) .+ 0
    dx, dy = rand(dirs), rand(dirs)
    if dx == 0 && dy == 0; dx = 1; end 
    
    new_pos = (clamp(a.pos[1] + dx, 1, Agents.spacesize(model)[1]),
                clamp(a.pos[2] + dy, 1, Agents.spacesize(model)[2]))
    
    agents_there = agents_in_position(new_pos, model)
    can_move = true
    for occ in agents_there
        if !(occ isa Key)
            can_move = false
        end
    end
    
    if can_move
        move_agent!(a, new_pos, model)
    end
end