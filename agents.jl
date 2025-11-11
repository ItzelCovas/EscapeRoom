using Agents
using Random
using LinearAlgebra

#Definicion del agente
@agent struct Ghost(GridAgent{2})
    type::String 
    has_key::Bool
    guarding_key::Bool
    target_key_pos::Union{Tuple{Int,Int}, Nothing}
end

#Definicion de la llave
@agent struct Key(GridAgent{2})
    is_hidden::Bool      # Empieza escondida (invisible)
    is_visible::Bool     # Ha aparecido en el mundo
    is_collected::Bool   # Ya la tiene el jugador
end

# 🔍 Función auxiliar: Buscar llaves visibles en todo el mapa
function find_nearest_visible_key(ghost_pos, model)
    """Encuentra la llave visible más cercana al fantasma"""
    nearest_key = nothing
    min_distance = Inf
    
    for agent in allagents(model)
        if agent isa Key && agent.is_visible && !agent.is_collected
            # Calcular distancia Manhattan (más eficiente para grids)
            distance = abs(ghost_pos[1] - agent.pos[1]) + abs(ghost_pos[2] - agent.pos[2])
            
            if distance < min_distance
                min_distance = distance
                nearest_key = agent
            end
        end
    end
    
    return nearest_key, min_distance
end

# 🔍 Función auxiliar: Verificar si la llave vigilada sigue visible
function is_key_still_there(key_pos, model)
    """Verifica si la llave en esa posición aún existe y está visible"""
    for agent in allagents(model)
        if agent isa Key && agent.pos == key_pos
            return agent.is_visible && !agent.is_collected
        end
    end
    return false
end

# Comportamiento del agente
function agent_step!(agent, model)
    if agent isa Ghost
        # 🛡️ MODO 1: Si está vigilando una llave
        if agent.guarding_key && !isnothing(agent.target_key_pos)
            # Verificar si la llave sigue ahí
            if is_key_still_there(agent.target_key_pos, model)
                @info "Fantasma vigilando llave en $(agent.target_key_pos) desde $(agent.pos)"
                # NO SE MUEVE - se queda vigilando
                return
            else
                # La llave fue recolectada o desapareció
                @info "Llave recolectada - Fantasma deja de vigilar"
                agent.guarding_key = false
                agent.target_key_pos = nothing
                agent.has_key = false
                # Continuar con búsqueda normal
            end
        end
        
        # 🎯 MODO 2: Buscar la llave visible más cercana
        target_key, distance = find_nearest_visible_key(agent.pos, model)
        
        if !isnothing(target_key)
            # Hay una llave visible -> perseguirla
            target_pos = target_key.pos
            
            @info "Fantasma en $(agent.pos) persiguiendo llave en $(target_pos) (distancia: $distance)"
            
            # ✅ Verificar si ya llegó a la llave
            if agent.pos == target_pos
                # ¡Alcanzó la llave! Activar modo vigilancia
                agent.has_key = true
                agent.guarding_key = true
                agent.target_key_pos = target_pos
                @info "¡Fantasma alcanzó la llave en $(target_pos)! Ahora la vigila."
                return  # No se mueve más
            end
            
            # Calcular dirección óptima (Manhattan)
            dx = target_pos[1] - agent.pos[1]
            dy = target_pos[2] - agent.pos[2]
            
            # Moverse primero en el eje con mayor diferencia
            if abs(dx) > abs(dy)
                # Moverse en X primero
                new_x = agent.pos[1] + sign(dx)
                new_pos = (new_x, agent.pos[2])
            else
                # Moverse en Y primero
                new_y = agent.pos[2] + sign(dy)
                new_pos = (agent.pos[1], new_y)
            end
            
            # Verificar límites del espacio
            size = Agents.spacesize(model)
            if 1 <= new_pos[1] <= size[1] && 1 <= new_pos[2] <= size[2]
                # Mover al fantasma (puede atravesar llaves, no verifica colisión)
                move_agent!(agent, new_pos, model)
                @info "➡️ Fantasma movido a $(new_pos)"
            end
        else
            # No hay llaves visibles, movimiento aleatorio (patrulla)
            @info "Fantasma patrullando (no hay llaves visibles)"
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
    ghost = Ghost(
        1,              # id
        (5, 5),         # posición inicial
        "ghost",        # type
        false,          # has_key
        false,          # guarding_key ✨
        nothing         # target_key_pos ✨
    )
    add_agent_pos!(ghost, model)
    @info "Fantasma creado en posición (5, 5)"

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
        @info "Llave $i creada en posición $pos (escondida)"
    end

    return model
end

#model = initialize_model()