using Agents
using Random
using LinearAlgebra

#Definicion del agente
@agent struct Ghost(GridAgent{2})
    type::String 
    has_key::Bool
end

#Definicion de la llave
@agent struct Key(GridAgent{2})
    is_hidden::Bool      # Empieza escondida (invisible)
    is_visible::Bool     # Ha aparecido en el mundo
    is_collected::Bool   # Ya la tiene el jugador
end

# 🔍 Función auxiliar: Buscar en círculo creciente
function search_in_radius(center_pos, radius, model)
"""Busca LA única llave visible dentro de un radio específico"""
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

#Comportamiento del agente
function agent_step!(agent, model)
    if agent isa Ghost
        # 🎯 BÚSQUEDA EN CÍRCULOS CONCÉNTRICOS CRECIENTES
        max_search_radius = 15  # Radio máximo de búsqueda
        search_step = 2.0       # Incremento del radio en cada iteración
        
        target_pos = nothing
        found_distance = nothing

        # Buscar desde radio pequeño hasta grande (solo hay UNA llave visible)
        for radius in 1.0:search_step:max_search_radius
            result = search_in_radius(agent.pos, radius, model)
            
            if !isnothing(result)
                target_key, distance = result
                target_pos = target_key.pos
                found_distance = distance
                
                @info "🔍 Fantasma detectó llave en $(target_pos) (radio: $radius, dist: $(round(distance, digits=2)))"
                break
            end
        end

        # Si encontró LA llave visible, moverse hacia ella
        if !isnothing(target_pos)
            #Calcular dirección hacia la llave
            dx = sign(target_pos[1] - agent.pos[1])
            dy = sign(target_pos[2] - agent.pos[2])
            new_pos = (agent.pos[1] + dx, agent.pos[2] + dy)

            # Verificar límites del espacio
            size = Agents.spacesize(model)
            if 1 <= new_pos[1] <= size[1] && 1 <= new_pos[2] <= size[2]
                # Mover al fantasma si la celda está libre
                if isempty(agents_in_position(new_pos, model))
                    move_agent!(agent, new_pos, model)
                end
            end

            # Verificar si alcanzó la llave
            if agent.pos == target_pos
                agent.has_key = true
                @info "¡Fantasma atrapó la llave en $(agent.pos)!"
            end
        else
            # No hay llaves visibles, movimiento aleatorio (patrulla)
            randomwalk!(agent, model)
        end
    end
end

#Inicializar modelo
function initialize_model(; size=(10,10), key_positions=[])
    space = GridSpace(size; periodic = false, metric = :manhattan)

    # Crear el modelo con agent_step!
    model = StandardABM(
        Union{Ghost, Key}, 
        space; 
        agent_step! = agent_step!,
        scheduler = Schedulers.Randomly()
    )

    #model = ABM(Union{Ghost, Key}, space; scheduler=Schedulers.Randomly)

    # CORRECCIÓN: add_agent! ahora usa la posición directamente
    #add_agent!((1, 1), Ghost, model; type="ghost", has_key=false)

    # CORRECCIÓN: (Tipo, model; kwargs...) sin especificar posición, se asigna automáticamente
    # O especificar posición: add_agent!(model, Tipo; pos=(x,y), kwargs...)
   
    # Crear agentes directamente y agregarlos
    #ghost = Ghost(id=nagents(model)+1, pos=(1, 1), type="ghost", has_key=false)
    # Agregar fantasma en posición (5, 5) - centro del tablero
    ghost = Ghost(1, (5, 5), "ghost", false)
    add_agent_pos!(ghost, model)

    #Fantasma rastreador
    #add_agent!(Ghost, (1,1), model; type="ghost", has_key=false)

    # Agregar llaves en posiciones específicas (todas empiezan ESCONDIDAS)
    for (i, pos) in enumerate(key_positions)
        key = Key(
            i + 1,           # id
            pos,             # posición
            true,            # is_hidden = true (empieza escondida)
            false,           # is_visible = false
            false            # is_collected = false
        )
        add_agent_pos!(key, model)
    end

    return model
end

#model = initialize_model()