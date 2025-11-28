using Agents
using Random
using LinearAlgebra

# Agentes 
@agent struct Ghost(GridAgent{2})
    type::String
    has_key::Bool
    is_evil::Bool
end

@agent struct Key(GridAgent{2})
    is_hidden::Bool     
    is_visible::Bool    
    is_collected::Bool  
end

# Buscar llave 
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

# Comportamiento del fantasma
function agent_step!(agent, model)
    if agent isa Ghost
        # --- Si es MALVADO (busca llaves) ---
        if agent.is_evil
            max_search_radius = 5.0
            search_step = 2.0
            target_key = nothing
            target_pos = nothing

            for radius in 1.0:search_step:max_search_radius
                result = search_in_radius(agent.pos, radius, model)
                if !isnothing(result)
                    target_key, distance = result
                    target_pos = target_key.pos
                    break
                end
            end

            if !isnothing(target_pos)
                dx = sign(target_pos[1] - agent.pos[1])
                dy = sign(target_pos[2] - agent.pos[2])
                new_pos = (agent.pos[1] + dx, agent.pos[2] + dy)
                
                size = Agents.spacesize(model)
                if 1 <= new_pos[1] <= size[1] && 1 <= new_pos[2] <= size[2]
                    if isempty(agents_in_position(new_pos, model))
                        move_agent!(agent, new_pos, model)
                    end
                end

                if agent.pos == target_pos
                    agent.has_key = true
                    target_key.is_collected = true
                    target_key.is_visible = false
                    @info "👻 Fantasma ROBÓ la llave!"
                end
            else
                randomwalk!(agent, model)
            end
        else
            # Si es bueno (random) 
            randomwalk!(agent, model)
        end
    end
end

# Inicializar modelo 
function initialize_model(; size=(10,10), key_positions=[])
    space = GridSpace(size; periodic=false, metric = :manhattan)
    model = StandardABM(Union{Ghost, Key}, space; agent_step! = agent_step!, scheduler = Schedulers.Randomly(), warn=false)

    # ID para el fantasma: 1
    # Ghost(id, pos, tipo, tiene_llave, es_malo)
    ghost = Ghost(1, (5, 5), "ghost", false, false)
    add_agent_own_pos!(ghost, model) 

    # ID para las llaves: 2 en adelante
    # contador 'i' empieza en 1, así que + 1 para que el primer ID sea 2
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
    if isempty(agents_in_position(new_pos, model))
        move_agent!(a, new_pos, model)
    end
end