using Agents
using Random
using LinearAlgebra

# ========== Agentes ==========
@agent struct Ghost(GridAgent{2})
    type::String
    has_key::Bool
end

@agent struct Key(GridAgent{2})
    is_hidden::Bool     # Empieza escondida (no visible)
    is_visible::Bool    # Aparece en el mundo
    is_collected::Bool  # Ya la tomó el jugador
end

# ========== Util: buscar una (única) llave visible dentro de un radio ==========
function search_in_radius(center_pos::NTuple{2,Int}, radius::Real, model)
    for agent in allagents(model)
        if agent isa Key && agent.is_visible && !agent.is_collected
            # distancia Euclídea en la grilla
            distance = sqrt(sum((center_pos .- agent.pos).^2))
            if distance <= radius
                return (agent, distance)
            end
        end
    end
    return nothing
end

# ========== Comportamiento del fantasma ==========
function agent_step!(agent, model)
    if agent isa Ghost
        # --- BÚSQUEDA EN CÍRCULOS CONCÉNTRICOS ---
        max_search_radius = 15.0
        search_step = 2.0

        target_key = nothing
        target_pos = nothing
        found_distance = nothing

        for radius in 1.0:search_step:max_search_radius
            result = search_in_radius(agent.pos, radius, model)
            if !isnothing(result)
                target_key, distance = result
                target_pos = target_key.pos
                found_distance = distance
                @debug "👻 Fantasma detectó llave en $(target_pos) (r=$radius, d=$(round(distance,digits=2)))"
                break
            end
        end

        if !isnothing(target_pos)
            # --- Moverse 8-direcciones hacia la llave ---
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
                @info "👻 Fantasma atrapó la llave en $(agent.pos)!"
            end
        else
            # Patrulla aleatoria (random walk con límites)
            randomwalk!(agent, model)
        end
    end
end

# ========== Inicializar modelo ==========
function initialize_model(; size=(10,10), key_positions=[])
    space = GridSpace(size; periodic=false, metric = :manhattan)

    model = StandardABM(
        Union{Ghost, Key},
        space;
        agent_step! = agent_step!,
        scheduler = Schedulers.Randomly()
    )

    # Fantasma al centro
    ghost = Ghost(1, (5, 5), "ghost", false)
    add_agent_pos!(ghost, model)

    # Llaves (todas empiezan ESCONDIDAS)
    for (i, pos) in enumerate(key_positions)
        key = Key(
            i + 1,
            pos,
            true,   # is_hidden
            false,  # is_visible
            false,  # is_collected
        )
        add_agent_pos!(key, model)
    end

    return model
end

# Random walk respetando límites (8 dirs)
function randomwalk!(a::Ghost, model)
    dirs = (-1:1) .+ 0
    dx, dy = rand(dirs), rand(dirs)
    new_pos = (clamp(a.pos[1] + dx, 1, Agents.spacesize(model)[1]),
               clamp(a.pos[2] + dy, 1, Agents.spacesize(model)[2]))
    if isempty(agents_in_position(new_pos, model))
        move_agent!(a, new_pos, model)
    end
end